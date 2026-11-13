#include <errno.h>
#include <stddef.h>
#include <stdio.h>
#include <string.h>
#include <sys/types.h>

typedef struct _snd_rawmidi snd_rawmidi_t;
int snd_rawmidi_open(snd_rawmidi_t **, snd_rawmidi_t **, const char *, int);
ssize_t snd_rawmidi_read(snd_rawmidi_t *, void *, size_t);
int snd_rawmidi_close(snd_rawmidi_t *);
int fake_open_calls(void);
int fake_read_calls(void);
int fake_close_calls(void);

int main(void) {
    snd_rawmidi_t *input = NULL;
    unsigned char bytes[8] = {0};
    if (snd_rawmidi_open(&input, NULL, "fake:device", 1) != 0 || errno != EBUSY) return 1;
    if (!input || fake_open_calls() != 1) return 2;
    if (snd_rawmidi_read(input, bytes, sizeof(bytes)) != 3 || errno != EAGAIN) return 3;
    if (memcmp(bytes, "\x90\x3c\x64", 3) != 0 || fake_read_calls() != 1) return 4;
    if (snd_rawmidi_close(input) != -EIO || errno != EIO || fake_close_calls() != 1) return 5;
    puts("PASS: open/read/close forwarded once; return values, errno and bytes preserved");
    return 0;
}
