import subprocess
import os
import time
import sys
import threading

# GPU Scheduler that watches queues/active.txt for new experiments
# Usage: python3 infra/gpu_scheduler.py

def get_gpu_status():
    """Returns a list of GPU utilization percentages from nvidia-smi"""
    try:
        result = subprocess.run(
            ['nvidia-smi', '--query-gpu=index', '--format=csv,noheader,nounits'],
            capture_output=True, text=True, check=True
        )
        return [int(x) for x in result.stdout.strip().split('\n')]
    except Exception as e:
        print(f"Error getting GPU status: {e}")
        return []

def run_experiment(gpu_id, name, steps, env):
    """Starts a subprocess to run the experiment on a specific GPU"""
    cmd_env = os.environ.copy()
    cmd_env["CUDA_VISIBLE_DEVICES"] = str(gpu_id)
    cmd_env.update(env)
    
    # We use run_experiment.sh which handles logging and results dir
    log_file = f"logs/{name}_parallel.log"
    print(f"🚀 Starting {name} on GPU {gpu_id}. Logging to {log_file}")
    
    # Create logs directory if it doesn't exist
    os.makedirs("logs", exist_ok=True)
    
    with open(log_file, "a") as f:
        return subprocess.Popen(
            ["bash", "infra/run_experiment.sh", name, str(steps)],
            env=cmd_env,
            stdout=f, stderr=subprocess.STDOUT,
            stdin=subprocess.DEVNULL,
            cwd=os.getcwd(),
        )

def load_queue():
    """Reads queues/active.txt and returns list of (name, steps, env_dict)"""
    queue_path = "queues/active.txt"
    if not os.path.exists(queue_path):
        return []
    
    experiments = []
    with open(queue_path, "r") as f:
        lines = f.readlines()
    
    for line in lines:
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        
        # Format: <name> <steps> [ENV_VAR=value ...]
        parts = line.split()
        if len(parts) < 2:
            continue
            
        name = parts[0]
        steps = parts[1]
        env = {}
        for part in parts[2:]:
            if "=" in part:
                k, v = part.split("=", 1)
                env[k] = v
        
        experiments.append((name, steps, env))
    
    return experiments

def pop_from_queue(name):
    """Removes the line starting with name from queues/active.txt"""
    queue_path = "queues/active.txt"
    if not os.path.exists(queue_path):
        return
    with open(queue_path, "r") as f:
        lines = f.readlines()
    
    with open(queue_path, "w") as f:
        found = False
        for line in lines:
            if not found and line.strip().startswith(name):
                found = True
                continue
            f.write(line)

def main():
    gpu_ids = get_gpu_status()
    if not gpu_ids:
        print("❌ No GPUs found.")
        sys.exit(1)
    
    print(f"🔍 Found {len(gpu_ids)} GPUs: {gpu_ids}")
    
    running_processes = {} # gpu_id -> (Popen object, name)

    print("🛰  Scheduler watching queues/active.txt (Append experiments there)")
    
    # Main loop
    while True:
        # Check running processes
        finished_gpus = []
        for gpu_id, (proc, name) in running_processes.items():
            if proc.poll() is not None:
                print(f"✅ Experiment '{name}' finished on GPU {gpu_id}")
                finished_gpus.append(gpu_id)
        
        for gpu_id in finished_gpus:
            del running_processes[gpu_id]
        
        # Try to assign new experiments from queues/active.txt
        queue = load_queue()
        if queue:
            for gpu_id in gpu_ids:
                if gpu_id not in running_processes:
                    if not queue:
                        break
                    name, steps, env = queue.pop(0)
                    proc = run_experiment(gpu_id, name, steps, env)
                    running_processes[gpu_id] = (proc, name)
                    pop_from_queue(name)
        
        # Idle wait
        time.sleep(10)

if __name__ == "__main__":
    main()
