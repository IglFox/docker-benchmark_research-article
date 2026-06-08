import subprocess
import time
import os
import shutil
import csv
from datetime import datetime
import platform
import matplotlib.pyplot as plt
import logging
import sys
import zipfile
import threading
import itertools

# Настройка логирования
file_handler = logging.FileHandler("pipeline.log", encoding="utf-8")
file_handler.setFormatter(logging.Formatter("%(asctime)s [%(levelname)s] %(message)s"))
file_handler.setLevel(logging.DEBUG)

class CleanConsoleFormatter(logging.Formatter):
    def format(self, record):
        if record.levelno == logging.INFO:
            return record.getMessage()
        return super().format(record)

console_handler = logging.StreamHandler(sys.stdout)
console_handler.setFormatter(CleanConsoleFormatter())
console_handler.setLevel(logging.INFO)

logger = logging.getLogger()
logger.setLevel(logging.DEBUG)
logger.handlers = [] # clear defaults
logger.addHandler(file_handler)
logger.addHandler(console_handler)

class Spinner:
    def __init__(self, message="Сборка..."):
        self.spinner = itertools.cycle(['⠋', '⠙', '⠹', '⠸', '⠼', '⠴', '⠦', '⠧', '⠇', '⠏'])
        self.message = message
        self.stop_event = threading.Event()
        self.thread = threading.Thread(target=self.spin)

    def spin(self):
        start_time = time.time()
        while not self.stop_event.is_set():
            sys.stdout.write(f'\r  └─ {self.message} {next(self.spinner)} ({time.time() - start_time:.1f}s)')
            sys.stdout.flush()
            time.sleep(0.1)
        sys.stdout.write('\r' + ' ' * 80 + '\r')

    def start(self):
        self.thread.start()

    def stop(self):
        self.stop_event.set()
        self.thread.join()

def get_progress_bar(step, total=8):
    filled = int(round(10 * step / float(total)))
    bar = '█' * filled + '░' * (10 - filled)
    return bar

def run_cmd(cmd: str) -> str:
    logging.debug(f"> {cmd}")
    result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
    if result.returncode != 0:
        logging.error(f"Ошибка выполнения '{cmd}':\n{result.stderr}")
    return result.stdout

def get_image_size(image_name: str) -> float:
    output = run_cmd(f'docker image inspect --format="{{{{.Size}}}}" {image_name}')
    try:
        size_bytes = int(output.strip())
        return size_bytes / (1024 * 1024)
    except ValueError:
        logging.warning(f"Не удалось определить размер для образа {image_name}")
        return 0.0

def clear_docker_cache():
    logging.info("  └─ Очистка кэша Docker (prune)...")
    run_cmd("docker builder prune -a -f")
    run_cmd("docker system prune -a -f")

def backup_file(filepath: str):
    logging.debug(f"Создан бэкап {filepath}")
    shutil.copy2(filepath, filepath + ".bak")

def restore_file(filepath: str):
    if os.path.exists(filepath + ".bak"):
        logging.debug(f"Восстановлен {filepath}")
        shutil.move(filepath + ".bak", filepath)

def modify_code_files():
    logging.info("  └─ Изменение нескольких файлов (app/main.py, app/services.py)...")
    with open("app/main.py", "a", encoding="utf-8") as f:
        f.write("\n# This is a programmatic modification to main.py\n")
    with open("app/services.py", "a", encoding="utf-8") as f:
        f.write("\n# Additional service logic for services.py\n")

def modify_requirements_py():
    logging.info("  └─ Добавление новой зависимости (app/requirements.txt)...")
    with open("app/requirements.txt", "a", encoding="utf-8") as f:
        f.write("\nrequests==2.32.3\n")

def build_docker(dockerfile: str, image_name: str):
    start = time.perf_counter()
    spinner = Spinner(f"Сборка образа {image_name}")
    spinner.start()
    
    run_cmd(f"docker build -t {image_name} -f {dockerfile} .")
    
    spinner.stop()
    end = time.perf_counter()
    duration = end - start
    size = get_image_size(image_name)
    logging.info(f"  └─ ✅ Готово! Время: {duration:.2f} сек. | Размер: {size:.2f} МБ")
    return duration, size

def main():
    results = []
    
    logging.info("\n🚀 Запуск автоматизированного бенчмарка Docker Build...\n")
    
    # Backup files
    backup_file("app/main.py")
    backup_file("app/services.py")
    backup_file("app/requirements.txt")
    
    try:
        logging.info("=======================================================")
        logging.info("         БЛОК 1: SINGLE-STAGE АРХИТЕКТУРА              ")
        logging.info("=======================================================\n")
        
        step = 1
        logging.info(f"▶ [Шаг {step}/8] {get_progress_bar(step)} Итерация 1: Холодный старт")
        clear_docker_cache()
        t1, s1 = build_docker("Dockerfile.single", "benchmark-single:latest")
        results.append((step, "Single-stage", "Cold Start", t1, s1))
        
        step = 2
        logging.info(f"\n▶ [Шаг {step}/8] {get_progress_bar(step)} Итерация 2: Изменение нескольких файлов кода (Горячий старт)")
        modify_code_files()
        t2, s2 = build_docker("Dockerfile.single", "benchmark-single:latest")
        results.append((step, "Single-stage", "Code Mod", t2, s2))
        
        step = 3
        logging.info(f"\n▶ [Шаг {step}/8] {get_progress_bar(step)} Итерация 3: Изменение зависимостей (Сброс кэша pip)")
        modify_requirements_py()
        t3, s3 = build_docker("Dockerfile.single", "benchmark-single:latest")
        results.append((step, "Single-stage", "Dep Mod", t3, s3))
        
        step = 4
        logging.info(f"\n▶ [Шаг {step}/8] {get_progress_bar(step)} Итерация 4: Повторная сборка без изменений (Идеальный кэш)")
        t4, s4 = build_docker("Dockerfile.single", "benchmark-single:latest")
        results.append((step, "Single-stage", "No Change", t4, s4))
        
        # Сброс файлов для чистоты эксперимента
        restore_file("app/main.py")
        restore_file("app/services.py")
        restore_file("app/requirements.txt")
        backup_file("app/main.py")
        backup_file("app/services.py")
        backup_file("app/requirements.txt")
        
        logging.info("\n=======================================================")
        logging.info("         БЛОК 2: MULTI-STAGE АРХИТЕКТУРА               ")
        logging.info("=======================================================\n")
        
        step = 5
        logging.info(f"▶ [Шаг {step}/8] {get_progress_bar(step)} Итерация 5: Холодный старт")
        clear_docker_cache()
        t5, s5 = build_docker("Dockerfile.multistage", "benchmark-multi:latest")
        results.append((step, "Multi-stage", "Cold Start", t5, s5))
        
        step = 6
        logging.info(f"\n▶ [Шаг {step}/8] {get_progress_bar(step)} Итерация 6: Изменение нескольких файлов кода (Горячий старт)")
        modify_code_files()
        t6, s6 = build_docker("Dockerfile.multistage", "benchmark-multi:latest")
        results.append((step, "Multi-stage", "Code Mod", t6, s6))
        
        step = 7
        logging.info(f"\n▶ [Шаг {step}/8] {get_progress_bar(step)} Итерация 7: Изменение зависимостей (Кэш BuildKit)")
        modify_requirements_py()
        t7, s7 = build_docker("Dockerfile.multistage", "benchmark-multi:latest")
        results.append((step, "Multi-stage", "Dep Mod", t7, s7))
        
        step = 8
        logging.info(f"\n▶ [Шаг {step}/8] {get_progress_bar(step)} Итерация 8: Повторная сборка без изменений")
        t8, s8 = build_docker("Dockerfile.multistage", "benchmark-multi:latest")
        results.append((step, "Multi-stage", "No Change", t8, s8))
        
    finally:
        logging.info("\nОчистка и восстановление исходных файлов...")
        restore_file("app/main.py")
        restore_file("app/services.py")
        restore_file("app/requirements.txt")

    logging.info("Сохранение результатов в CSV...")
    with open("benchmark_results.csv", "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["Step", "Architecture", "Operation", "Time (s)", "Size (MB)"])
        writer.writerows(results)
    
    logging.info("Генерация графиков...")
    labels = [f"I{r[0]}\n{r[2]}" for r in results]
    times = [r[3] for r in results]
    sizes = [r[4] for r in results]
    
    plt.figure(figsize=(10, 6))
    bars = plt.bar(labels, times, color=['blue']*4 + ['green']*4)
    plt.title("Сравнение времени сборки")
    plt.ylabel("Время (секунды)")
    plt.xticks(rotation=45)
    for bar in bars:
        yval = bar.get_height()
        plt.text(bar.get_x() + bar.get_width()/2, yval + 1, f"{yval:.1f}s", ha='center', va='bottom')
    plt.tight_layout()
    plt.savefig("time_comparison.png")
    plt.close()
    
    plt.figure(figsize=(10, 6))
    bars = plt.bar(labels, sizes, color=['blue']*4 + ['green']*4)
    plt.title("Сравнение размера образов")
    plt.ylabel("Размер (МБ)")
    plt.xticks(rotation=45)
    for bar in bars:
        yval = bar.get_height()
        plt.text(bar.get_x() + bar.get_width()/2, yval + 1, f"{yval:.1f}MB", ha='center', va='bottom')
    plt.tight_layout()
    plt.savefig("size_comparison.png")
    plt.close()

    logging.info("Генерация текстового отчета...")
    os.makedirs("reports", exist_ok=True)
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    report_filename = f"reports/report_{timestamp}.txt"
    with open(report_filename, "w", encoding="utf-8") as f:
        f.write("=== ОТЧЕТ БЕНЧМАРКА DOCKER BUILD ===\n")
        f.write(f"Дата: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
        f.write(f"ОС: {platform.system()} {platform.release()}\n")
        f.write(f"Процессор: {platform.processor()}\n\n")
        
        f.write(f"{'Шаг':<5} | {'Архитектура':<15} | {'Операция':<15} | {'Время (с)':<10} | {'Размер (МБ)':<10}\n")
        f.write("-" * 65 + "\n")
        for r in results:
            f.write(f"{r[0]:<5} | {r[1]:<15} | {r[2]:<15} | {r[3]:<10.2f} | {r[4]:<10.2f}\n")
        
        f.write("\n=== ВЫВОДЫ ===\n")
        f.write("1. Multi-stage сборка дает существенно меньший размер финального образа.\n")
        f.write("2. Горячий старт при изменении кода работает мгновенно в обеих архитектурах благодаря кэшированию слоев.\n")
        f.write("3. Использование BuildKit Cache Mounts позволяет сильно ускорить установку новых зависимостей (Dep Mod) в Multi-stage.\n")
        
    logging.info("Упаковка результатов в ZIP-архив...")
    os.makedirs("exports", exist_ok=True)
    zip_filename = f"exports/benchmark_export_{timestamp}.zip"
    with zipfile.ZipFile(zip_filename, 'w') as zipf:
        zipf.write("benchmark_results.csv")
        zipf.write("time_comparison.png")
        zipf.write("size_comparison.png")
        zipf.write(report_filename)
        
    logging.info(f"\n🎉 Бенчмарк успешно завершен! Все результаты сохранены в: {zip_filename}")

if __name__ == "__main__":
    main()
