#include <stdbool.h>
#include <stdio.h>
#include <stdlib.h>
#include <unistd.h>
#include <time.h>

#include <cadef.h>


static chid channel_id;
static evid event_id;
static int updates = 0;
static int64_t start;
static int last_updates = 0;

static int64_t get_time(void)
{
    struct timespec now;
    clock_gettime(CLOCK_REALTIME, &now);
    return (int64_t) now.tv_sec * 1000000 + now.tv_nsec / 1000;
}

static void on_connect(struct connection_handler_args args)
{
    printf("Connected: %p, %ld\n", args.chid, args.op);
}

static void on_update(struct event_handler_args args)
{
    printf(".");
    fflush(stdout);
    updates += 1;

    int64_t now = get_time();
    if (now - start >= 1000000)
    {
        printf("tick: %d\n", updates - last_updates);
        last_updates = updates;
        start = now;
    }
}

int main(int argc, const char **argv)
{
    int count = 0;
    if (argc > 1)
        count = atoi(argv[1]);

    ca_context_create(ca_disable_preemptive_callback);
    ca_create_channel(
        "ARAVISCAM1:ARR:ArrayData", on_connect, NULL, 0, &channel_id);
    ca_create_subscription(
        DBR_CHAR, count, channel_id, DBE_VALUE, on_update, NULL, &event_id);

    start = get_time();
    while (true)
    {
        ca_pend_event(1e-3);
        usleep(10000);
    }
    return 0;
}
