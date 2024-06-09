import psutil

def find_process(exeName):
    most_recent_proc = None
    most_recent_time = -1

    for proc in psutil.process_iter(['name', 'create_time']):
        try:
            if proc.info['name'] == exeName:
                if proc.info['create_time'] > most_recent_time:
                    most_recent_proc = proc
                    most_recent_time = proc.info['create_time']
        except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
            continue
    return most_recent_proc

def terminate_process(exeName):
    process = find_process(exeName)
    process and process.terminate()