#include <stdbool.h>
#include <stdio.h>
#include <stdlib.h>
#include <unistd.h>
#include <signal.h>
#include <time.h>

#include <cadef.h>


#define PV      "SR-DI-DCCT-01:SIGNAL"


#define TEST_EPICS(action) \
    ( { \
        int rc = (action); \
        if (rc != ECA_NORMAL) \
            fprintf(stderr, "Oops: error %d on line %d\n", \
                rc, __LINE__); \
        rc == ECA_NORMAL; \
    } )


static chid channel_id;


// static int64_t get_time(void)
// {
//     struct timespec now;
//     clock_gettime(CLOCK_REALTIME, &now);
//     return (int64_t) now.tv_sec * 1000000 + now.tv_nsec / 1000;
// }

static void on_connect(struct connection_handler_args args)
{
    printf("Connected: %p, %ld\n", args.chid, args.op);
}

static void on_update(struct event_handler_args args)
{
    printf("Updated\n");
}


int main(int argc, const char **argv)
{
    TEST_EPICS(ca_context_create(ca_enable_preemptive_callback));

    TEST_EPICS(ca_create_channel(PV, on_connect, NULL, 0, &channel_id));
    sleep(1);

    TEST_EPICS(ca_array_get_callback(
        DBR_DOUBLE, 1, channel_id, on_update, NULL));
    TEST_EPICS(ca_flush_io());
    sleep(1);

    TEST_EPICS(ca_array_get_callback(
        DBR_DOUBLE, 1, channel_id, on_update, NULL));
    TEST_EPICS(ca_flush_io());
    sleep(1);

    return 0;
}
