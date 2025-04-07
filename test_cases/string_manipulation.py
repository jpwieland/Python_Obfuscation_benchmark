"""
Caso de teste com operações intensivas de string
"""
import random
import time
import hashlib

def generate_random_string(length):
    """Gera uma string aleatória de comprimento especificado"""
    chars = "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789"
    return ''.join(random.choice(chars) for _ in range(length))

def string_operations(input_string):
    """Realiza várias operações com strings"""
    # Operações de concatenação
    result = ""
    for i in range(100):
        result += input_string[:10] + str(i)
    
    # Operações de substituição
    for char in "aeiou":
        result = result.replace(char, char.upper())
    
    # Operações de divisão
    parts = result.split('A')
    
    # Operações de junção
    new_result = '-'.join(parts[:100])
    
    # Codificação e hash
    encoded = new_result.encode('utf-8')
    hashed = hashlib.sha256(encoded).hexdigest()
    
    return len(result), len(new_result), hashed

def main():
    # Gerar strings aleatórias
    strings = [generate_random_string(1000) for _ in range(100)]
    
    # Processar strings
    start_time = time.time()
    results = []
    
    for s in strings:
        results.append(string_operations(s))
    
    end_time = time.time()
    
    # Apresentar resultados
    print(f"Processadas {len(strings)} strings em {end_time - start_time:.3f} segundos")
    print(f"Último hash gerado: {results[-1][2][:20]}...")

if __name__ == "__main__":
    main()