import csv
import random

def generate_mock_dataset(filename="mock_rfm_data.csv", rows=200):
    with open(filename, mode='w', newline='') as file:
        writer = csv.writer(file)
        writer.writerow(['customer_id', 'recency', 'frequency', 'monetary'])
        
        for i in range(1, rows + 1):
            recency = random.randint(1, 365)
            frequency = random.randint(1, 80)
            monetary = round(random.uniform(15.0, 5000.0), 2)
            writer.writerow([i, recency, frequency, monetary])

    print(f"Generated {rows} rows in {filename}")

if __name__ == '__main__':
    generate_mock_dataset()