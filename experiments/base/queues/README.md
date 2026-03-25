# Queue Policy

`queues/active.txt` is the only live execution queue in this repo.

Use the queue directories like this:

- `queues/active.txt`: the only file workers, schedulers, and queue runners may execute
- `queues/*_plan.md`: proposed wave plans and approved payloads in markdown form
- `queues/archive/`: retired queue payloads kept only for provenance and historical reruns

To rerun an archived batch:

```bash
cp queues/archive/<group>/<queue>.txt queues/active.txt
bash infra/run_queue.sh queues/active.txt
```

All execution helpers in `infra/` should reject any queue path other than `queues/active.txt`.
