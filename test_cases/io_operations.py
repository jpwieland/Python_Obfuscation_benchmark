"""
Caso de teste com operações de I/O
"""
import os
import time
import json
import tempfile
import random

def generate_data(num_records):
    """Gera dados aleatórios para teste"""
    data = []
    for i in range(num_records):
        record = {
            "id": i,
            "name": f"Item-{i}",
            "value": random.uniform(0, 1000),
            "tags": [random.choice(["red", "green", "blue", "yellow", "orange"]) for _ in range(3)],
            "active": random.choice([True, False]),
            "priority": random.randint(1, 10)
        }
        data.append(record)
    return data

def write_files(base_dir, data, num_files):
    """Escreve dados em múltiplos arquivos"""
    os.makedirs(base_dir, exist_ok=True)
    
    chunk_size = len(data) // num_files
    files_written = []
    
    for i in range(num_files):
        start_idx = i * chunk_size
        end_idx = start_idx + chunk_size if i < num_files - 1 else len(data)
        
        chunk = data[start_idx:end_idx]
        filename = os.path.join(base_dir, f"data_{i}.json")
        
        with open(filename, 'w') as f:
            json.dump(chunk, f)
        
        files_written.append(filename)
    
    return files_written

def read_and_process_files(filenames):
    """Lê e processa arquivos"""
    all_data = []
    
    for filename in filenames:
        with open(filename, 'r') as f:
            data = json.load(f)
            all_data.extend(data)
    
    # Processar dados
    active_items = [item for item in all_data if item["active"]]
    high_priority = [item for item in all_data if item["priority"] >= 8]
    value_sum = sum(item["value"] for item in all_data)
    
    return len(all_data), len(active_items), len(high_priority), value_sum

def main():
    # Criar diretório temporário
    temp_dir = tempfile.mkdtemp(prefix="benchmark_io_")
    
    try:
        # Gerar dados
        print("Gerando dados...")
        data = generate_data(10000)
        
        # Escrever arquivos
        print("Escrevendo arquivos...")
        start_time = time.time()
        files = write_files(temp_dir, data, 20)
        write_time = time.time() - start_time
        
        # Ler e processar arquivos
        print("Lendo e processando arquivos...")
        start_time = time.time()
        total, active, high_priority, value_sum = read_and_process_files(files)
        read_time = time.time() - start_time
        
        # Apresentar resultados
        print(f"Escrita concluída em {write_time:.3f} segundos")
        print(f"Leitura concluída em {read_time:.3f} segundos")
        print(f"Processados {total} itens, {active} ativos, {high_priority} alta prioridade")
        print(f"Soma total de valores: {value_sum:.2f}")
        
    finally:
        # Limpar diretório temporário
        for filename in os.listdir(temp_dir):
            file_path = os.path.join(temp_dir, filename)
            try:
                os.unlink(file_path)
            except:
                pass
        os.rmdir(temp_dir)

if __name__ == "__main__":
    main()