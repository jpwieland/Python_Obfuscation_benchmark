"""
Caso de teste com operações intensivas de CPU
"""
import time
import math
import random

def prime_check(num):
    """Verifica se um número é primo"""
    if num < 2:
        return False
    for i in range(2, int(math.sqrt(num)) + 1):
        if num % i == 0:
            return False
    return True

def matrix_multiply(matrix_a, matrix_b):
    """Multiplicação de matrizes"""
    rows_a = len(matrix_a)
    cols_a = len(matrix_a[0])
    cols_b = len(matrix_b[0])
    
    result = [[0 for _ in range(cols_b)] for _ in range(rows_a)]
    
    for i in range(rows_a):
        for j in range(cols_b):
            for k in range(cols_a):
                result[i][j] += matrix_a[i][k] * matrix_b[k][j]
    
    return result

def main():
    # Encontrar números primos
    prime_count = 0
    for i in range(1000, 10000):
        if prime_check(i):
            prime_count += 1
    
    print(f"Números primos encontrados: {prime_count}")
    
    # Criar matrizes aleatórias
    size = 100
    matrix_a = [[random.random() for _ in range(size)] for _ in range(size)]
    matrix_b = [[random.random() for _ in range(size)] for _ in range(size)]
    
    # Multiplicar matrizes
    start_time = time.time()
    result = matrix_multiply(matrix_a, matrix_b)
    end_time = time.time()
    
    print(f"Multiplicação de matriz {size}x{size} concluída em {end_time - start_time:.3f} segundos")
    print(f"Valor da matriz resultado[0][0]: {result[0][0]:.6f}")

if __name__ == "__main__":
    main()