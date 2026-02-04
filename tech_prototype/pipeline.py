import time
import concurrent.futures
from filters import filter_1_get_tickers, filter_2_check_date, filter_3_fetch_data


def run_pipeline():
    start_time = time.time()

    print("=========================================")
    print("STARTING CRYPTO DATA PIPELINE")
    print("=========================================")

    symbols = filter_1_get_tickers()

    if not symbols:
        print("Грешка: Не се пронајдени симболи.")
        return

    MAX_WORKERS = 20

    print(f"\nЗапочнува обработка со {MAX_WORKERS} нитки...")

    with concurrent.futures.ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
        filter_2_results = list(executor.map(filter_2_check_date, symbols))

        tasks_to_download = [item for item in filter_2_results if item[1] is not None]

        print(f"Потребно ажурирање за {len(tasks_to_download)} од {len(symbols)} валути.")

        futures = [executor.submit(filter_3_fetch_data, item) for item in tasks_to_download]

        counter = 0
        for future in concurrent.futures.as_completed(futures):
            counter += 1
            result = future.result()
            if counter % 50 == 0:
                print(f"[{counter}/{len(tasks_to_download)}] {result}")

    end_time = time.time()
    duration = end_time - start_time

    print("\n=========================================")
    print(f"Вкупно време на извршување: {duration:.2f} секунди")  #
    print("=========================================")


if __name__ == "__main__":
    run_pipeline()