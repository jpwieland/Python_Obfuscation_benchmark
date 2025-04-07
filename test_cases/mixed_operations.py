"""
Caso de teste com uma mistura de diferentes tipos de operações
"""
import os
import time
import random
import math
import json
import tempfile

class DataProcessor:
    def __init__(self, data_size):
        self.data = self._generate_data(data_size)
        self.processed = False
        self.results = {}
    
    def _generate_data(self, size):
        """Gera dados sintéticos para processamento"""
        return {
            "values": [random.uniform(-100, 100) for _ in range(size)],
            "flags": [random.choice([True, False]) for _ in range(size)],
            "categories": [random.choice(["A", "B", "C", "D"]) for _ in range(size)],
            "text": [f"Item {i} with random text {self._generate_random_text(20)}" for i in range(size)]
        }
    
    def _generate_random_text(self, length):
        """Gera texto aleatório"""
        chars = "abcdefghijklmnopqrstuvwxyz "
        return ''.join(random.choice(chars) for _ in range(length))
    
    def process(self):
        """Processa os dados com várias operações"""
        # Computação numérica
        start_time = time.time()
        positive_values = [v for v in self.data["values"] if v > 0]
        negative_values = [v for v in self.data["values"] if v < 0]
        
        stats = {
            "mean": sum(self.data["values"]) / len(self.data["values"]),
            "std_dev": math.sqrt(sum((x - sum(self.data["values"]) / len(self.data["values"]))**2 for x in self.data["values"]) / len(self.data["values"])),
            "min": min(self.data["values"]),
            "max": max(self.data["values"]),
            "positive_count": len(positive_values),
            "negative_count": len(negative_values)
        }
        
        # Transformações de dados
        transformed = []
        for i in range(len(self.data["values"])):
            transformed.append({
                "value": self.data["values"][i],
                "flag": self.data["flags"][i],
                "category": self.data["categories"][i],
                "text": self.data["text"][i],
                "score": self.data["values"][i] * (2 if self.data["flags"][i] else 0.5)
            })
        
        # Processamento de string
        category_counts = {}
        word_counts = {}
        
        for i in range(len(self.data["categories"])):
            category = self.data["categories"][i]
            category_counts[category] = category_counts.get(category, 0) + 1
            
            words = self.data["text"][i].lower().split()
            for word in words:
                word_counts[word] = word_counts.get(word, 0) + 1
        
        # Escrita de arquivo temporário
        temp_file = tempfile.mktemp(suffix=".json")
        with open(temp_file, 'w') as f:
            json.dump({
                "stats": stats,
                "category_counts": category_counts,
                "common_words": sorted(word_counts.items(), key=lambda x: x[1], reverse=True)[:50]
            }, f)
        
        # Leitura de arquivo
        with open(temp_file, 'r') as f:
            loaded_data = json.load(f)
        
        # Limpar arquivo temporário
        os.unlink(temp_file)
        
        # Definir resultados
        self.results = {
            "processing_time": time.time() - start_time,
            "stats": stats,
            "category_distribution": category_counts,
            "top_words": dict(sorted(word_counts.items(), key=lambda x: x[1], reverse=True)[:10]),
            "transformed_sample": transformed[:5]
        }
        
        self.processed = True
        return self.results
    
    def report(self):
        """Exibe um relatório dos resultados"""
        if not self.processed:
            print("Os dados ainda não foram processados.")
            return
        
        print(f"Processamento concluído em {self.results['processing_time']:.3f} segundos")
        print("\nEstatísticas Numéricas:")
        for key, value in self.results["stats"].items():
            print(f"  {key}: {value:.4f}")
        
        print("\nDistribuição de Categorias:")
        for key, value in self.results["category_distribution"].items():
            print(f"  {key}: {value}")
        
        print("\nPalavras Mais Comuns:")
        for word, count in self.results["top_words"].items():
            print(f"  {word}: {count}")

def main():
    print("Inicializando processador de dados...")
    processor = DataProcessor(10000)
    
    print("Iniciando processamento...")
    start_time = time.time()
    processor.process()
    end_time = time.time()
    
    print(f"Processamento concluído em {end_time - start_time:.3f} segundos")
    processor.report()

if __name__ == "__main__":
    main()