#define _GNU_SOURCE
typedef struct _snd_rawmidi snd_rawmidi_t;
#include <dlfcn.h>
#include <errno.h>
#include <pthread.h>
#include <stdatomic.h>
#include <stdbool.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <time.h>
#include <unistd.h>

#define LS_QUEUE_CAPACITY 256u
#define LS_NAME_CAPACITY 128u
#define LS_CAPTURE_CAPACITY 256u
#define LS_HANDLE_CAPACITY 64u
#define LS_LOG_PATH "/tmp/lockstep-observer.log"

typedef int (*rawmidi_open_fn)(snd_rawmidi_t **, snd_rawmidi_t **, const char *, int);
typedef ssize_t (*rawmidi_read_fn)(snd_rawmidi_t *, void *, size_t);
typedef int (*rawmidi_close_fn)(snd_rawmidi_t *);

typedef enum { REC_OPEN = 1, REC_READ = 2, REC_CLOSE = 3 } record_type;
typedef struct {
    record_type type;
    uint64_t monotonic_ns;
    uintptr_t handle;
    int mode;
    size_t length;
    bool truncated;
    char name[LS_NAME_CAPACITY];
    unsigned char bytes[LS_CAPTURE_CAPACITY];
} record;
typedef struct { _Atomic uint64_t sequence; record value; } queue_slot;
static queue_slot queue_slots[LS_QUEUE_CAPACITY];
static _Atomic uint64_t enqueue_pos;
static _Atomic uint64_t dequeue_pos;
static _Atomic uint64_t dropped_records;
static _Atomic bool observer_active;
static _Atomic bool worker_running;
static pthread_t worker_thread;
static char target_name[LS_NAME_CAPACITY];

typedef struct { _Atomic uintptr_t handle; _Atomic bool capture; } handle_slot;
static handle_slot handles[LS_HANDLE_CAPACITY];
static _Atomic(rawmidi_open_fn) next_open;
static _Atomic(rawmidi_read_fn) next_read;
static _Atomic(rawmidi_close_fn) next_close;

static uint64_t now_ns(void) {
    struct timespec ts;
    if (clock_gettime(CLOCK_MONOTONIC, &ts) != 0) return 0;
    return (uint64_t)ts.tv_sec * 1000000000ull + (uint64_t)ts.tv_nsec;
}

/* Bounded-retry MPMC queue: MIDI read hooks never wait for the log worker. */
static bool queue_push(const record *value) {
    uint64_t pos = atomic_load_explicit(&enqueue_pos, memory_order_relaxed);
    for (unsigned attempt = 0; attempt < 4; ++attempt) {
        queue_slot *slot = &queue_slots[pos & (LS_QUEUE_CAPACITY - 1u)];
        uint64_t seq = atomic_load_explicit(&slot->sequence, memory_order_acquire);
        int64_t diff = (int64_t)(seq - pos);
        if (diff == 0) {
            if (atomic_compare_exchange_weak_explicit(&enqueue_pos, &pos, pos + 1,
                    memory_order_relaxed, memory_order_relaxed)) {
                slot->value = *value;
                atomic_store_explicit(&slot->sequence, pos + 1, memory_order_release);
                return true;
            }
        } else if (diff < 0) {
            atomic_fetch_add_explicit(&dropped_records, 1, memory_order_relaxed);
            return false;
        } else {
            pos = atomic_load_explicit(&enqueue_pos, memory_order_relaxed);
        }
    }
    atomic_fetch_add_explicit(&dropped_records, 1, memory_order_relaxed);
    return false;
}

static bool queue_pop(record *value) {
    uint64_t pos = atomic_load_explicit(&dequeue_pos, memory_order_relaxed);
    for (;;) {
        queue_slot *slot = &queue_slots[pos & (LS_QUEUE_CAPACITY - 1u)];
        uint64_t seq = atomic_load_explicit(&slot->sequence, memory_order_acquire);
        int64_t diff = (int64_t)(seq - (pos + 1));
        if (diff == 0) {
            if (atomic_compare_exchange_weak_explicit(&dequeue_pos, &pos, pos + 1,
                    memory_order_relaxed, memory_order_relaxed)) {
                *value = slot->value;
                atomic_store_explicit(&slot->sequence, pos + LS_QUEUE_CAPACITY, memory_order_release);
                return true;
            }
        } else if (diff < 0) {
            return false;
        } else {
            pos = atomic_load_explicit(&dequeue_pos, memory_order_relaxed);
        }
    }
}

static void emit_record(record_type type, snd_rawmidi_t *handle, int mode,
                        const char *name, const void *bytes, size_t length) {
    record item;
    memset(&item, 0, sizeof(item));
    item.type = type;
    item.monotonic_ns = now_ns();
    item.handle = (uintptr_t)handle;
    item.mode = mode;
    if (name) snprintf(item.name, sizeof(item.name), "%s", name);
    if (bytes && length) {
        item.length = length < LS_CAPTURE_CAPACITY ? length : LS_CAPTURE_CAPACITY;
        item.truncated = length > LS_CAPTURE_CAPACITY;
        memcpy(item.bytes, bytes, item.length);
    }
    (void)queue_push(&item);
}

static void *log_worker(void *unused) {
    (void)unused;
    FILE *log = fopen(LS_LOG_PATH, "a");
    record item;
    while (atomic_load_explicit(&worker_running, memory_order_acquire) ||
           atomic_load_explicit(&dequeue_pos, memory_order_relaxed) !=
           atomic_load_explicit(&enqueue_pos, memory_order_relaxed)) {
        if (!queue_pop(&item)) {
            struct timespec pause = { .tv_sec = 0, .tv_nsec = 5000000 };
            nanosleep(&pause, NULL);
            continue;
        }
        if (!log) continue;
        fprintf(log, "t=%llu ", (unsigned long long)item.monotonic_ns);
        if (item.type == REC_OPEN) {
            fprintf(log, "OPEN mode=%d handle=%p name=%s\n", item.mode,
                    (void *)item.handle, item.name);
        } else if (item.type == REC_READ) {
            fprintf(log, "READ handle=%p bytes=", (void *)item.handle);
            for (size_t i = 0; i < item.length; ++i) fprintf(log, "%02X", item.bytes[i]);
            fprintf(log, "%s\n", item.truncated ? " [TRUNCATED]" : "");
        } else if (item.type == REC_CLOSE) {
            fprintf(log, "CLOSE handle=%p\n", (void *)item.handle);
        }
        fflush(log);
    }
    uint64_t drops = atomic_load_explicit(&dropped_records, memory_order_relaxed);
    if (log && drops) fprintf(log, "DROPPED_RECORDS=%llu\n", (unsigned long long)drops);
    if (log) fclose(log);
    return NULL;
}

static bool executable_is_mpc(void) {
    char path[256];
    ssize_t n = readlink("/proc/self/exe", path, sizeof(path) - 1);
    if (n <= 0) return false;
    path[n] = '\0';
    return strcmp(path, "/usr/bin/MPC") == 0;
}

static handle_slot *find_handle(snd_rawmidi_t *handle) {
    uintptr_t wanted = (uintptr_t)handle;
    for (size_t i = 0; i < LS_HANDLE_CAPACITY; ++i) {
        if (atomic_load_explicit(&handles[i].handle, memory_order_acquire) == wanted)
            return &handles[i];
    }
    return NULL;
}

__attribute__((constructor)) static void lockstep_init(void) {
    for (uint64_t i = 0; i < LS_QUEUE_CAPACITY; ++i)
        atomic_store_explicit(&queue_slots[i].sequence, i, memory_order_relaxed);
    const char *enabled = getenv("LOCKSTEP_DIAGNOSTIC_ENABLE");
    const char *target = getenv("LOCKSTEP_TARGET_ALSA_NAME");
    if (!executable_is_mpc() || !enabled || strcmp(enabled, "1") != 0) return;
    if (target && target[0]) snprintf(target_name, sizeof(target_name), "%s", target);
    atomic_store_explicit(&observer_active, true, memory_order_release);
    atomic_store_explicit(&worker_running, true, memory_order_release);
    if (pthread_create(&worker_thread, NULL, log_worker, NULL) != 0) {
        atomic_store_explicit(&observer_active, false, memory_order_release);
        atomic_store_explicit(&worker_running, false, memory_order_release);
    }
}

__attribute__((destructor)) static void lockstep_shutdown(void) {
    if (atomic_exchange_explicit(&worker_running, false, memory_order_acq_rel))
        pthread_join(worker_thread, NULL);
}

int snd_rawmidi_open(snd_rawmidi_t **input, snd_rawmidi_t **output,
                     const char *name, int mode) {
    rawmidi_open_fn real_open = atomic_load_explicit(&next_open, memory_order_acquire);
    if (!real_open) {
        rawmidi_open_fn resolved = (rawmidi_open_fn)dlsym(RTLD_NEXT, "snd_rawmidi_open");
        if (resolved) atomic_compare_exchange_strong(&next_open, &real_open, resolved);
        real_open = atomic_load_explicit(&next_open, memory_order_acquire);
    }
    if (!real_open) { errno = ENOSYS; return -ENOSYS; }
    int result = real_open(input, output, name, mode);
    int saved_errno = errno;
    if (result >= 0 && atomic_load_explicit(&observer_active, memory_order_acquire)) {
        snd_rawmidi_t *opened = (input && *input) ? *input : NULL;
        emit_record(REC_OPEN, opened, mode, name, NULL, 0);
        if (opened && target_name[0] && name && strcmp(name, target_name) == 0) {
            for (size_t i = 0; i < LS_HANDLE_CAPACITY; ++i) {
                uintptr_t empty = 0;
                if (atomic_compare_exchange_strong_explicit(&handles[i].handle, &empty,
                        (uintptr_t)opened, memory_order_acq_rel, memory_order_relaxed)) {
                    atomic_store_explicit(&handles[i].capture, true, memory_order_release);
                    break;
                }
            }
        }
    }
    errno = saved_errno;
    return result;
}

ssize_t snd_rawmidi_read(snd_rawmidi_t *rawmidi, void *buffer, size_t size) {
    rawmidi_read_fn real_read = atomic_load_explicit(&next_read, memory_order_acquire);
    if (!real_read) {
        rawmidi_read_fn resolved = (rawmidi_read_fn)dlsym(RTLD_NEXT, "snd_rawmidi_read");
        if (resolved) atomic_compare_exchange_strong(&next_read, &real_read, resolved);
        real_read = atomic_load_explicit(&next_read, memory_order_acquire);
    }
    if (!real_read) { errno = ENOSYS; return -ENOSYS; }
    ssize_t result = real_read(rawmidi, buffer, size);
    int saved_errno = errno;
    if (result > 0 && buffer && atomic_load_explicit(&observer_active, memory_order_acquire)) {
        handle_slot *slot = find_handle(rawmidi);
        if (slot && atomic_load_explicit(&slot->capture, memory_order_acquire))
            emit_record(REC_READ, rawmidi, 0, NULL, buffer,
                        (size_t)result < size ? (size_t)result : size);
    }
    errno = saved_errno;
    return result;
}

int snd_rawmidi_close(snd_rawmidi_t *rawmidi) {
    rawmidi_close_fn real_close = atomic_load_explicit(&next_close, memory_order_acquire);
    if (!real_close) {
        rawmidi_close_fn resolved = (rawmidi_close_fn)dlsym(RTLD_NEXT, "snd_rawmidi_close");
        if (resolved) atomic_compare_exchange_strong(&next_close, &real_close, resolved);
        real_close = atomic_load_explicit(&next_close, memory_order_acquire);
    }
    if (!real_close) { errno = ENOSYS; return -ENOSYS; }
    if (atomic_load_explicit(&observer_active, memory_order_acquire)) {
        handle_slot *slot = find_handle(rawmidi);
        if (slot) {
            atomic_store_explicit(&slot->capture, false, memory_order_release);
            atomic_store_explicit(&slot->handle, 0, memory_order_release);
        }
        emit_record(REC_CLOSE, rawmidi, 0, NULL, NULL, 0);
    }
    int result = real_close(rawmidi);
    int saved_errno = errno;
    errno = saved_errno;
    return result;
}
