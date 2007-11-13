#include <strings.h>
#include <stdlib.h>

#include "cadef.h"
#include "db_access.h"

void check(int rc)
{
    if (rc != ECA_NORMAL)
    {
        printf("Failed: %d - %s\n", rc, ca_message(rc));
        exit(1);
    }
}

void dump(char * buffer, int length)
{
    int i;
    for (i = 0; i < length; i++)
    {
        printf(" %02x", buffer[i]);
        if ((i+1) % 16 == 0)
            printf("\n");
    }
}

int main(int argc, char **argv)
{
    chid channel;
    check(ca_create_channel(argv[1], NULL, NULL, 0, &channel));
    printf("Created channel %d\n", channel);

    ca_pend_event(1.0);
    printf("Maybe we're connected?\n");

    char Strings[80];
    memset(Strings, 0, 80);
    strcpy(Strings, "1.2345");
    strcpy(Strings+40, "6.789");
    check(ca_array_put(DBR_STRING, 2, channel, Strings));
    printf("Put strings ok\n");

    ca_pend_event(1.0);
    printf("Maybe we've sent it now?\n");

    memset(Strings, 0, 80);
    check(ca_array_get(DBR_STRING, 2, channel, Strings));
    check(ca_pend_io(1.0));
    printf("Maybe we've sent it now?\n");

    printf("Strings[0]: %s\n", Strings);
    printf("Strings[1]: %s\n", Strings+40);
    dump(Strings, 80);
}
