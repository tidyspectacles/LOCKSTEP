#include <errno.h>
#include <stddef.h>
#include <sys/types.h>

typedef struct _snd_rawmidi snd_rawmidi_t;
static int handle_storage;
static int opens, reads, closes;

int snd_rawmidi_open(snd_rawmidi_t **input, snd_rawmidi_t **output,
                     const char *name, int mode) {
    (void)output; (void)name; (void)mode;
    ++opens;
    if (input) *input = (snd_rawmidi_t *)&handle_storage;
    errno = EBUSY;
    return 0;
}

ssize_t snd_rawmidi_read(snd_rawmidi_t *handle, void *buffer, size_t size) {
    (void)handle;
    ++reads;
    if (size < 3) return -1;
    ((unsigned char *)buffer)[0] = 0x90;
    ((unsigned char *)buffer)[1] = 60;
    ((unsigned char *)buffer)[2] = 100;
    errno = EAGAIN;
    return 3;
}

int snd_rawmidi_close(snd_rawmidi_t *handle) {
    (void)handle;
    ++closes;
    errno = EIO;
    return -EIO;
}

int fake_open_calls(void) { return opens; }
int fake_read_calls(void) { return reads; }
int fake_close_calls(void) { return closes; }
