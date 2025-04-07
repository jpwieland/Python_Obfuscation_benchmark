#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Benchmark de Estratégias de Ofuscação de Código Python
"""

import os
import sys
import time
import subprocess
import psutil
import json
import statistics
import matplotlib.pyplot as plt
import numpy as np
from pathlib import Path
import logging
import tempfile
import shutil
import argparse
import importlib.util
import platform
import re
import distutils.spawn
import shlex

# Configuração de logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("ObfuscationBenchmark")

# Definição das ferramentas de ofuscação
TOOLS = {
    'original': {
        'description': 'Código original sem ofuscação',
        'enabled': True
    },
    'pyarmor7': {
        'description': 'PyArmor v7 - Ferramenta comercial com proteção avançada',
        'install': 'pip install pyarmor==7.7.4',
        'command': 'pyarmor-7 obfuscate {input_file} -O {output_dir}',
        'output': '{output_dir}/dist/{input_name}.py',
        'enabled': True,
        'check_version': True
    },
    'pyarmor_gen': {
        'description': 'PyArmor 8+ com comando gen',
        'install': 'pip install pyarmor',
        'command': 'pyarmor gen {input_file}',  # Comando corrigido
        'output': 'dist/{input_name}.py',
        'enabled': True
    },
    'pyminifier': {
        'description': 'Minificação e ofuscação básica',
        'install': 'pip install pyminifier',
        'command': 'python -m pyminifier {input_file} > {output_file}', 
        'output': '{output_dir}/{input_name}.min.py',
        'enabled': True
    },
    'opy': {
        'description': 'Ofuscação baseada em manipulação de AST',
        'install': 'pip install https://github.com/QQuick/Opy/archive/master.zip',
        'command': 'python -c "from opy.tool import main; import sys; sys.argv = [\'\', \'-o\', \'{output_file}\', \'{input_file}\']; main()"',
        'output': '{output_dir}/{input_name}.opy.py',
        'enabled': False
    },
    'pyobfuscate': {
        'description': 'Ofuscação básica',
        'install': 'pip install git+https://github.com/astrand/pyobfuscate.git',
        'command': 'pyobfuscate -i {input_file} > {output_temp}',  # Saída para arquivo temporário
        'output': '{output_dir}/{input_name}.obf.py',
        'post_process': True,  # Indica que é necessário processamento após ofuscação
        'enabled': True
    },
    'cython': {
        'description': 'Compilação para código C como ofuscação',
        'install': 'pip install cython',
        'enabled': True,
        'custom_handler': True  # Indica que usa um manipulador personalizado
    },
    'pyinstaller': {
        'description': 'Empacotamento com ofuscação básica',
        'install': 'pip install pyinstaller',
        'command': 'pyinstaller --onefile {input_file} --distpath {output_dir}',
        'output': '{output_dir}/{input_name}',
        'enabled': True,
        'needs_execution': True,  # Indica que a saída é um executável
        'check_env': True  # Verificar compatibilidade com o ambiente
    }
}

# Métricas a serem avaliadas
METRICS = {
    'execution_time': {
        'description': 'Tempo de execução (segundos)',
        'unit': 's',
        'higher_is_better': False
    },
    'memory_usage': {
        'description': 'Uso de memória (MB)',
        'unit': 'MB',
        'higher_is_better': False
    },
    'code_size': {
        'description': 'Tamanho do código (KB)',
        'unit': 'KB',
        'higher_is_better': False
    },
    'startup_time': {
        'description': 'Tempo de inicialização (ms)',
        'unit': 'ms',
        'higher_is_better': False
    }
}

class ObfuscationBenchmark:
    def __init__(self, test_files, output_dir='results', iterations=5):
        self.test_files = test_files
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(exist_ok=True, parents=True)
        self.iterations = iterations
        self.results = {}
        self.temp_dir = Path(tempfile.mkdtemp(prefix="obfuscation_benchmark_"))
        logger.info(f"Usando diretório temporário: {self.temp_dir}")
        
        # Fazer verificações adicionais do ambiente
        self.check_environment()
    
    def cleanup(self):
        """Limpa arquivos temporários."""
        try:
            shutil.rmtree(self.temp_dir)
            logger.info(f"Diretório temporário removido: {self.temp_dir}")
        except Exception as e:
            logger.warning(f"Erro ao remover diretório temporário: {e}")
    

    def _check_opy_path(self):
        """Verifica o caminho correto do módulo opy."""
        try:
            import opy
            
            # Verificar se __file__ existe e não é None
            if not hasattr(opy, '__file__') or opy.__file__ is None:
                logger.warning("Módulo opy encontrado, mas __file__ é None")
                # Tentar encontrar o caminho de outra forma
                spec = importlib.util.find_spec('opy')
                if spec and spec.origin:
                    opy_path = os.path.dirname(spec.origin)
                    logger.info(f"Módulo opy localizado via spec: {opy_path}")
                else:
                    logger.warning("Não foi possível determinar o caminho do módulo opy")
                    return None
            else:
                logger.info(f"Módulo opy encontrado em: {opy.__file__}")
                opy_path = os.path.dirname(opy.__file__)
            
            # Verificar possíveis nomes da ferramenta
            possible_tool_paths = [
                os.path.join(opy_path, "opy_tool.py"),
                os.path.join(opy_path, "tool.py"),
            ]
            for path in possible_tool_paths:
                if os.path.exists(path):
                    tool_name = os.path.basename(path).split('.')[0]
                    logger.info(f"Ferramenta opy encontrada: {tool_name}")
                    return tool_name
                    
            # Se chegou aqui, nenhuma ferramenta foi encontrada
            logger.warning(f"Nenhuma ferramenta opy encontrada em: {opy_path}")
            return None
        except ImportError:
            logger.warning("Módulo opy não pôde ser importado")
            return None


    def detect_dependencies(self, test_file):
        """Detecta arquivos Python importados pelo arquivo de teste."""
        logger.info(f"Detectando dependências para {test_file}...")
        dependencies = []
        
        try:
            with open(test_file, 'r') as f:
                content = f.read()
            
            # Buscar por importações no formato:
            # from X import Y
            # import X
            
            import re
            # Padrão para "from X import Y"
            from_imports = re.findall(r'from\s+([^\s.]+)\s+import', content)
            # Padrão para "import X" ou "import X as Y"
            direct_imports = re.findall(r'import\s+([^\s.,]+)', content)
            
            # Combinar todos os possíveis módulos importados
            potential_modules = set(from_imports + direct_imports)
            
            # Filtrar apenas os que podem ser arquivos locais
            for module in potential_modules:
                if module not in ['os', 'sys', 'time', 'math', 'numpy', 'cv2', 'dlib', 
                                'imutils', 'scipy', 'argparse', 'subprocess', 'importlib', 
                                'psutil', 'json', 'statistics', 'matplotlib', 'logging',
                                'tempfile', 'shutil', 'platform', 're', 'distutils', 'shlex']:
                    # Verificar se existe um arquivo .py correspondente
                    module_file = os.path.join(os.path.dirname(test_file), f"{module}.py")
                    if os.path.exists(module_file):
                        logger.info(f"Dependência encontrada: {module_file}")
                        dependencies.append(module_file)
                        
                        # Recursivamente verificar dependências deste arquivo
                        sub_dependencies = self.detect_dependencies(module_file)
                        dependencies.extend(sub_dependencies)
            
            return list(set(dependencies))  # Remover duplicatas
        except Exception as e:
            logger.error(f"Erro ao detectar dependências: {e}")
            return []


    def check_environment(self):
        """Verificar compatibilidade com o ambiente e ajustar ferramentas conforme necessário."""
        # Verificar versão do Python
        python_version = sys.version_info
        logger.info(f"Python versão: {python_version.major}.{python_version.minor}.{python_version.micro}")
        
        # Verificar se estamos no ambiente Anaconda
        in_anaconda = 'Anaconda' in sys.version or 'conda' in sys.version or 'anaconda' in sys.executable.lower()
        
        if in_anaconda:
            logger.info("Ambiente Anaconda detectado")
            
            # Verificar se há problemas com pathlib que afetam o PyInstaller
            if 'pyinstaller' in TOOLS and TOOLS['pyinstaller']['enabled']:
                try:
                    pathlib_path = importlib.util.find_spec('pathlib')
                    if pathlib_path and 'site-packages' in str(pathlib_path.origin):
                        logger.warning("Backport de pathlib detectado, que é incompatível com PyInstaller no Anaconda")
                        logger.warning("Desativando PyInstaller. Para usar, execute: conda remove pathlib")
                        TOOLS['pyinstaller']['enabled'] = False
                except:
                    pass
        
        # Python 3.11+ não é suportado pelo PyArmor 7
        if python_version.major == 3 and python_version.minor >= 11:
            if 'pyarmor7' in TOOLS and TOOLS['pyarmor7']['enabled']:
                logger.warning("Python 3.11+ não é suportado pelo PyArmor 7, desativando")
                TOOLS['pyarmor7']['enabled'] = False
        
        # Verificar opy
        if 'opy' in TOOLS and TOOLS['opy']['enabled']:
            opy_tool = self._check_opy_path()
            if opy_tool:
                # Atualizar o comando com o caminho correto
                TOOLS['opy']['command'] = f'python -c "from opy.{opy_tool} import main; import sys; sys.argv = [\'\', \'-o\', \'{{output_file}}\', \'{{input_file}}\']; main()"'
            else:
                logger.warning("Módulo opy não encontrado ou ferramentas não identificadas, tentando instalação")
                try:
                    subprocess.run(
                        "pip install -U https://github.com/QQuick/Opy/archive/master.zip",
                        shell=True, check=True, capture_output=True
                    )
                    # Verificar novamente após instalação
                    opy_tool = self._check_opy_path()
                    if opy_tool:
                        TOOLS['opy']['command'] = f'python -c "from opy.{opy_tool} import main; import sys; sys.argv = [\'\', \'-o\', \'{{output_file}}\', \'{{input_file}}\']; main()"'
                    else:
                        logger.warning("Falha ao identificar ferramentas opy, desativando")
                        TOOLS['opy']['enabled'] = False
                except:
                    logger.warning("Falha ao instalar opy, desativando")
                    TOOLS['opy']['enabled'] = False
        
        # Verificar se o PyArmor gen tem a sintaxe correta
        if 'pyarmor_gen' in TOOLS and TOOLS['pyarmor_gen']['enabled']:
            try:
                # Verificar versão do PyArmor
                result = subprocess.run(
                    ["pyarmor", "--version"], 
                    capture_output=True, 
                    text=True
                )
                version_output = result.stdout if result.stdout else result.stderr
                logger.info(f"PyArmor version: {version_output.strip()}")
                
                # Verificar se é v8+
                if "8." in version_output or "9." in version_output:
                    # Corrigir comando para PyArmor 8/9
                    TOOLS['pyarmor_gen']['command'] = 'pyarmor gen -O {output_dir}/dist {input_file}'
                    TOOLS['pyarmor_gen']['output'] = '{output_dir}/dist/{input_name}.py'
                else:
                    # Provavelmente não é compatível
                    logger.warning("PyArmor 8+ não detectado, desativando pyarmor_gen")
                    TOOLS['pyarmor_gen']['enabled'] = False
            except:
                logger.warning("Erro ao verificar versão do PyArmor, desativando pyarmor_gen")
                TOOLS['pyarmor_gen']['enabled'] = False
        
        # Verificar se o pyminifier3 é suportado ou se deve usar pyminifier
# Verificar se o pyminifier suporta a opção --no-obfuscate-variables
        if 'pyminifier' in TOOLS and TOOLS['pyminifier']['enabled']:
            try:
                result = subprocess.run(
                    ["python", "-m", "pyminifier", "--help"],
                    capture_output=True,
                    text=True
                )
                help_output = result.stdout
                
                if "--no-obfuscate" in help_output:
                    logger.info("pyminifier suporta --no-obfuscate, ajustando comando")
                    TOOLS['pyminifier']['command'] = 'python -m pyminifier --no-obfuscate {input_file} > {output_file}'
                elif "-O" in help_output or "--obfuscate" in help_output:
                    # Se ofuscação é opcional, podemos evitá-la
                    logger.info("pyminifier suporta opção de ofuscação, usando sem ela")
                    TOOLS['pyminifier']['command'] = 'python -m pyminifier {input_file} > {output_file}'
                else:
                    # Usar comando básico
                    logger.info("Usando comando básico para pyminifier")
                    TOOLS['pyminifier']['command'] = 'python -m pyminifier {input_file} > {output_file}'
            except:
                logger.warning("Erro ao verificar opções do pyminifier, usando comando básico")
                TOOLS['pyminifier']['command'] = 'python -m pyminifier {input_file} > {output_file}'
        # Verificar pyobfuscate
        if 'pyobfuscate' in TOOLS and TOOLS['pyobfuscate']['enabled']:
            # Verificar se a opção -k (preservar keywords) está disponível
            try:
                help_output = subprocess.run(
                    ["pyobfuscate", "--help"],
                    capture_output=True,
                    text=True
                )
                if "-k" in help_output.stdout or "--preserve-keywords" in help_output.stdout:
                    logger.info("pyobfuscate suporta preservação de keywords, ativando")
                    TOOLS['pyobfuscate']['command'] = 'pyobfuscate -k -i {input_file} > {output_temp}'
            except:
                logger.warning("Erro ao verificar opções do pyobfuscate, prosseguindo com configuração padrão")
    
    def _check_command_exists(self, command):
        """Verifica se um comando existe no sistema."""
        return distutils.spawn.find_executable(command.split()[0]) is not None
    
    def _check_module_installed(self, module_name):
        """Verifica se um módulo Python está instalado."""
        return importlib.util.find_spec(module_name) is not None
    
    def _execute_command(self, command, shell=True, cwd=None):
        """Executa um comando com melhor tratamento de erros"""
        logger.info(f"Executando comando: {command}")
        try:
            if not shell and isinstance(command, str):
                command = shlex.split(command)
            
            process = subprocess.run(
                command,
                shell=shell,
                check=True,
                capture_output=True,
                text=True,
                cwd=cwd
            )
            
            if process.stdout:
                logger.debug(f"Saída: {process.stdout}")
            
            return True, process.stdout
        except subprocess.CalledProcessError as e:
            logger.error(f"Comando falhou com código {e.returncode}: {command}")
            if e.stdout:
                logger.error(f"Stdout: {e.stdout}")
            if e.stderr:
                logger.error(f"Stderr: {e.stderr}")
            return False, (e.stdout, e.stderr)
    
    def install_tools(self):
        """Instala todas as ferramentas de ofuscação necessárias."""
        logger.info("Instalando ferramentas de ofuscação...")
        
        for tool_name, tool_info in TOOLS.items():
            if not tool_info.get('enabled', True):
                logger.info(f"Ferramenta {tool_name} está desativada, pulando instalação.")
                continue
                
            if tool_name == 'original':
                continue
            
            # Verificar se a ferramenta já está instalada
            if tool_name == 'pyarmor7' and self._check_command_exists('pyarmor-7'):
                logger.info(f"{tool_name} já está instalado.")
                continue
            elif tool_name == 'pyarmor_gen' and self._check_command_exists('pyarmor'):
                logger.info(f"{tool_name} já está instalado.")
                continue
            elif tool_name == 'pyminifier' and (self._check_module_installed('pyminifier') or self._check_module_installed('pyminifier3')):
                logger.info(f"{tool_name} já está instalado.")
                continue
            elif tool_name == 'opy' and self._check_module_installed('opy'):
                logger.info(f"{tool_name} já está instalado.")
                continue
            elif tool_name == 'pyobfuscate' and self._check_command_exists('pyobfuscate'):
                logger.info(f"{tool_name} já está instalado.")
                continue
            elif tool_name == 'cython' and self._check_module_installed('cython'):
                logger.info(f"{tool_name} já está instalado.")
                continue
            elif tool_name == 'pyinstaller' and self._check_module_installed('PyInstaller'):
                logger.info(f"{tool_name} já está instalado.")
                continue
                
            if 'install' in tool_info:
                logger.info(f"Instalando {tool_name}...")
                try:
                    success, output = self._execute_command(tool_info['install'])
                    if success:
                        logger.info(f"{tool_name} instalado com sucesso.")
                    else:
                        logger.error(f"Erro ao instalar {tool_name}")
                        logger.warning(f"O benchmark continuará, mas {tool_name} será ignorado.")
                        tool_info['enabled'] = False
                except Exception as e:
                    logger.error(f"Erro ao instalar {tool_name}: {e}")
                    logger.warning(f"O benchmark continuará, mas {tool_name} será ignorado.")
                    tool_info['enabled'] = False
    


    def _fix_pyobfuscate_output(self, output_file):
        try:
            if not os.path.exists(output_file):
                logger.error(f"Arquivo a ser corrigido não existe: {output_file}")
                return False
                    
            with open(output_file, 'r') as f:
                content = f.read()
            
            # Corrigir problema de __name__ substituído
            name_var_match = re.search(r'if\s+(\w+)\s*==\s*["\']__main__["\']', content)
            if name_var_match:
                var_name = name_var_match.group(1)
                logger.info(f"Corrigindo substituição de __name__ por {var_name}")
                content = f"{var_name} = __name__\n" + content
            
            # Corrigir vírgulas incorretas em chamadas de função
            # Corrige padrões como: tempfile.mkdtemp(, prefix="benchmark_io_")
            content = re.sub(r'([a-zA-Z0-9_.]+)\((,\s*)', r'\1(', content)
            
            # Corrigir chamadas np.array com argumentos ofuscados
            content = re.sub(r'np\.array\(\[([^]]*)\],\s*(\w+)=', r'np.array([\1], dtype=', content)
            
            # Corrigir substituições em funções comuns
            common_functions = [
                'os.makedirs', 
                'tempfile.mkdtemp', 
                'tempfile.mktemp', 
                'sorted',
                '.sort',
                'np.array'
            ]
            
            # Substituir parâmetros nomeados incorretos para nomes corretos
            param_mappings = {
                'os.makedirs': {'exist_ok': ['(?!exist_ok)\w+']},
                'tempfile.mkdtemp': {'prefix': ['(?!prefix)\w+']},
                'tempfile.mktemp': {'suffix': ['(?!suffix)\w+']},
                'sorted': {'key': ['(?!key|reverse)\w+'], 'reverse': ['(?!key|reverse)\w+']},
                '.sort': {'key': ['(?!key|reverse)\w+'], 'reverse': ['(?!key|reverse)\w+']},
                'np.array': {'dtype': ['(?!dtype)\w+']},
            }
            
            # Aplicar correções para cada função
            for func_name, param_dict in param_mappings.items():
                for correct_param, invalid_patterns in param_dict.items():
                    for pattern in invalid_patterns:
                        # Substitui parâmetros incorretos pelo correto
                        content = re.sub(
                            rf'{func_name}\((.*?),\s*{pattern}=',
                            f'{func_name}(\\1, {correct_param}=',
                            content
                        )
                        # Caso especial para o primeiro parâmetro
                        content = re.sub(
                            rf'{func_name}\(\s*{pattern}=',
                            f'{func_name}({correct_param}=',
                            content
                        )
            
            # Correção especial para np.array com argumentos inesperados
            # Remove completamente argumentos nomeados não reconhecidos
            content = re.sub(r'np\.array\(([^,]+),\s*\w+=([^)]+)\)', r'np.array(\1)', content)
            
            with open(output_file, 'w') as f:
                f.write(content)
            
            return True
        except Exception as e:
            logger.error(f"Erro ao corrigir arquivo pyobfuscate: {e}")
            return False
    
    
    def apply_obfuscation(self, tool_name, input_file):
        """Aplica a ferramenta de ofuscação ao arquivo."""
        # Detectar dependências do arquivo
        dependencies = self.detect_dependencies(input_file)
        logger.info(f"Dependências encontradas para {input_file}: {dependencies}")
        
        if tool_name == 'original':
            # Para o caso original, criar uma cópia do arquivo e suas dependências
            input_path = Path(input_file)
            output_path = self.temp_dir / f"{input_path.stem}_original{input_path.suffix}"
            shutil.copy2(input_file, output_path)
            
            # Copiar as dependências para o mesmo diretório
            for dep in dependencies:
                dep_path = Path(dep)
                dep_output = self.temp_dir / dep_path.name
                shutil.copy2(dep, dep_output)
                
            return str(output_path)
        
        tool_info = TOOLS[tool_name]
        
        if not tool_info.get('enabled', True):
            logger.warning(f"Ferramenta {tool_name} está desativada, pulando.")
            return None
        
        input_path = Path(input_file)
        input_dir = str(input_path.parent)
        input_name = input_path.stem
        output_dir = str(self.temp_dir)
        
        # Caso especial para Cython
        if tool_name == 'cython':
            # Primeiro ofuscar o arquivo principal
            main_output = self._apply_cython(input_file)
            
            # Em seguida, ofuscar cada dependência
            for dep in dependencies:
                dep_output = self._apply_cython(dep)
                
            return main_output
        
        # Para outras ferramentas, executar o comando de ofuscação
        if 'command' in tool_info:
            output_file = tool_info['output'].format(
                output_dir=output_dir,
                input_name=input_name,
                input_dir=input_dir
            )
            
            # Arquivo temporário para pyobfuscate
            output_temp = output_file
            if tool_name == 'pyobfuscate':
                output_temp = output_file + '.temp'
            
            # Garantir que o diretório de destino existe
            os.makedirs(os.path.dirname(output_file), exist_ok=True)
            
            command = tool_info['command'].format(
                input_file=input_file,
                output_file=output_file,
                output_temp=output_temp,
                input_name=input_name,
                input_dir=input_dir,
                output_dir=output_dir
            )
            
            try:
                # Executar comando e capturar resultado
                success, output = self._execute_command(command)
                
                if not success:
                    logger.error(f"Erro ao executar comando para {tool_name}")
                    return None
                
                # Pós-processamento para pyobfuscate
                if tool_name == 'pyobfuscate' and tool_info.get('post_process', False):
                    if os.path.exists(output_temp):
                        # Mover arquivo temporário para destino final se necessário
                        if output_temp != output_file:
                            shutil.move(output_temp, output_file)
                        # Corrigir problemas no arquivo ofuscado
                        self._fix_pyobfuscate_output(output_file)
                
                # Verificar se o arquivo de saída foi criado
                if not os.path.exists(output_file):
                    logger.error(f"Arquivo de saída não foi criado: {output_file}")
                    return None
                
                # Processar cada dependência com a mesma ferramenta
                for dep in dependencies:
                    dep_path = Path(dep)
                    dep_name = dep_path.stem
                    
                    # Ajustar o comando para a dependência
                    dep_output_file = tool_info['output'].format(
                        output_dir=output_dir,
                        input_name=dep_name,
                        input_dir=input_dir
                    )
                    
                    dep_output_temp = dep_output_file
                    if tool_name == 'pyobfuscate':
                        dep_output_temp = dep_output_file + '.temp'
                    
                    dep_command = tool_info['command'].format(
                        input_file=dep,
                        output_file=dep_output_file,
                        output_temp=dep_output_temp,
                        input_name=dep_name,
                        input_dir=input_dir,
                        output_dir=output_dir
                    )
                    
                    # Executar comando para a dependência
                    dep_success, dep_output = self._execute_command(dep_command)
                    
                    if not dep_success:
                        logger.warning(f"Erro ao processar dependência {dep} com {tool_name}, continuando...")
                    
                    # Pós-processamento para pyobfuscate na dependência
                    if tool_name == 'pyobfuscate' and tool_info.get('post_process', False):
                        if os.path.exists(dep_output_temp):
                            if dep_output_temp != dep_output_file:
                                shutil.move(dep_output_temp, dep_output_file)
                            self._fix_pyobfuscate_output(dep_output_file)
                
                logger.info(f"Ofuscação concluída: {output_file}")
                return output_file
            except Exception as e:
                logger.error(f"Erro ao executar comando: {e}")
                return None
        
        logger.error(f"Configuração inválida para ferramenta {tool_name}")
        return None


    def _apply_cython(self, input_file):
        """Aplica ofuscação usando Cython."""
        input_path = Path(input_file)
        input_name = input_path.stem
        
        # Criar cópia do arquivo no diretório temporário
        cython_file = self.temp_dir / f"{input_name}.pyx"
        shutil.copy2(input_file, cython_file)
        
        # Criar arquivo setup.py para compilação - SEM INDENTAÇÃO nas linhas
        setup_file = self.temp_dir / "setup.py"
        
        # Criar o conteúdo do setup.py sem indentação extra
        setup_content = 'from setuptools import setup\n'
        setup_content += 'from Cython.Build import cythonize\n\n'
        setup_content += 'setup(\n'
        setup_content += '    ext_modules = cythonize("{0}", compiler_directives={{"language_level": "3"}}),\n'
        setup_content += ')\n'
        setup_content = setup_content.format(cython_file.name)
        
        with open(setup_file, 'w') as f:
            f.write(setup_content)
        
        # Executar o comando de build do Cython
        logger.info(f"Compilando com Cython: {cython_file}")
        try:
            success, output = self._execute_command(
                f"cd {self.temp_dir} && python setup.py build_ext --inplace"
            )
            
            if not success:
                logger.error(f"Erro ao compilar com Cython")
                return None
            
            # Localizar o arquivo .so/.pyd gerado
            extension = ".pyd" if sys.platform == "win32" else ".so"
            compiled_files = list(self.temp_dir.glob(f"{input_name}*{extension}"))
            
            if not compiled_files:
                logger.error(f"Nenhum arquivo compilado encontrado para {input_name}")
                return None
            
            compiled_file = str(compiled_files[0])
            logger.info(f"Compilação com Cython concluída: {compiled_file}")
            
            # Detectar dependências para incluir no wrapper
            dependencies = []
            for dep in self.detect_dependencies(input_file):
                dep_path = Path(dep)
                dependencies.append(dep_path.stem)
            
            # Criar um script wrapper para carregar o módulo compilado
            wrapper_file = self.temp_dir / f"{input_name}_cython_wrapper.py"
            
            # Gerar imports para dependências
            dependency_imports = ""
            for dep in dependencies:
                dependency_imports += f"import {dep}\n"
            
            # Wrapper sem indentação extra
            wrapper_content = 'import sys\n'
            wrapper_content += 'import os\n'
            wrapper_content += 'sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))\n'
            if dependency_imports:
                wrapper_content += f'{dependency_imports}\n'
            wrapper_content += f'import {input_name}\n'
            wrapper_content += 'if __name__ == "__main__":\n'
            wrapper_content += f'    if hasattr({input_name}, "main"):\n'
            wrapper_content += f'        {input_name}.main()\n'
            
            with open(wrapper_file, 'w') as f:
                f.write(wrapper_content)
            
            return str(wrapper_file)
        except Exception as e:
            logger.error(f"Erro ao compilar com Cython: {e}")
            return None

    def measure_performance(self, tool_name, obfuscated_file):
        """Mede o desempenho do arquivo ofuscado."""
        if not obfuscated_file or not os.path.exists(obfuscated_file):
            logger.error(f"Arquivo ofuscado não encontrado: {obfuscated_file}")
            return None
        
        tool_info = TOOLS[tool_name]
        metrics = {metric: [] for metric in METRICS}
        
        # Determinar como executar o arquivo
        is_executable = tool_info.get('needs_execution', False)
        
        # Verificar se há recursos externos necessários
        resource_dir = os.path.dirname(self.test_files[0])
        
        # Copiar recursos necessários para o diretório temporário
        if os.path.exists(os.path.join(resource_dir, "dlib_shape_predictor")):
            target_dir = os.path.join(self.temp_dir, "dlib_shape_predictor")
            os.makedirs(target_dir, exist_ok=True)
            
            # Copiar o arquivo .dat se existir
            dat_file = os.path.join(resource_dir, "dlib_shape_predictor", "shape_predictor_68_face_landmarks.dat")
            if os.path.exists(dat_file):
                shutil.copy2(dat_file, target_dir)
        
        # Verificar e copiar video.mp4 se existir
        video_file = os.path.join(resource_dir, "video.mp4")
        if os.path.exists(video_file):
            shutil.copy2(video_file, self.temp_dir)
        
        logger.info(f"Medindo desempenho para {tool_name} ({obfuscated_file})...")
        for i in range(self.iterations):
            logger.info(f"Iteração {i+1}/{self.iterations}")
            try:
                # Medir tempo de inicialização
                start_time = time.time()
                
                # Executar no diretório temporário para acessar recursos copiados
                current_dir = os.getcwd()
                os.chdir(self.temp_dir)
                
                if is_executable:
                    process = subprocess.Popen([obfuscated_file], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
                else:
                    process = subprocess.Popen([sys.executable, obfuscated_file], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
                
                startup_time = (time.time() - start_time) * 1000  # ms
                metrics['startup_time'].append(startup_time)
                
                # Medir uso de memória (pico)
                try:
                    process_info = psutil.Process(process.pid)
                    memory_usage = 0
                    
                    # Monitorar uso de memória durante a execução
                    while process.poll() is None:
                        try:
                            current_memory = process_info.memory_info().rss / (1024 * 1024)  # MB
                            memory_usage = max(memory_usage, current_memory)
                            time.sleep(0.01)  # Pequeno intervalo
                        except (psutil.NoSuchProcess, psutil.AccessDenied):
                            break
                    
                    metrics['memory_usage'].append(memory_usage)
                except (psutil.NoSuchProcess, psutil.AccessDenied) as e:
                    logger.warning(f"Erro ao medir memória: {e}")
                
                # Medir tempo de execução total
                stdout, stderr = process.communicate()
                execution_time = time.time() - start_time
                metrics['execution_time'].append(execution_time)
                
                # Voltar ao diretório original
                os.chdir(current_dir)
                
                # Verificar se houve erros
                if process.returncode != 0:
                    logger.warning(f"Erro na execução: código {process.returncode}")
                    logger.warning(f"Saída: {stdout.decode() if stdout else ''}\n{stderr.decode() if stderr else ''}")
                    # Continuar mesmo com erros para coletar métricas da execução parcial
                
                # Medir tamanho do código
                code_size = os.path.getsize(obfuscated_file) / 1024  # KB
                metrics['code_size'].append(code_size)
                
                logger.info(f"Iteração {i+1} concluída: tempo={execution_time:.3f}s, memória={memory_usage:.2f}MB")
            except Exception as e:
                logger.error(f"Erro na iteração {i+1}: {e}")
        
        # Calcular estatísticas
        result = {}
        for metric in METRICS:
            if metrics[metric]:
                result[metric] = {
                    'mean': statistics.mean(metrics[metric]),
                    'median': statistics.median(metrics[metric]),
                    'min': min(metrics[metric]),
                    'max': max(metrics[metric]),
                    'stdev': statistics.stdev(metrics[metric]) if len(metrics[metric]) > 1 else 0
                }
            else:
                result[metric] = {'mean': 0, 'median': 0, 'min': 0, 'max': 0, 'stdev': 0}
        
        return result

    def run_benchmark(self):
        """Executa o benchmark para todas as ferramentas e arquivos de teste."""
        self.install_tools()
        
        for test_file in self.test_files:
            logger.info(f"Executando benchmark para {test_file}...")
            self.results[test_file] = {}
            
            for tool_name, tool_info in TOOLS.items():
                if not tool_info.get('enabled', True):
                    logger.info(f"Ferramenta {tool_name} está desativada, pulando.")
                    continue
                
                logger.info(f"Aplicando {tool_name} a {test_file}...")
                try:
                    obfuscated_file = self.apply_obfuscation(tool_name, test_file)
                    if obfuscated_file:
                        metrics = self.measure_performance(tool_name, obfuscated_file)
                        if metrics:
                            self.results[test_file][tool_name] = metrics
                            logger.info(f"{tool_name} concluído com sucesso")
                        else:
                            logger.error(f"Falha ao medir desempenho para {tool_name}")
                    else:
                        logger.error(f"Falha ao aplicar {tool_name}")
                except Exception as e:
                    logger.error(f"Erro ao processar {tool_name}: {str(e)}")
        
        # Salvar resultados
        self.save_results()
    
    def save_results(self):
        """Salva os resultados do benchmark em um arquivo JSON."""
        if not self.results:
            logger.error("Nenhum resultado para salvar.")
            return
        
        results_file = self.output_dir / "benchmark_results.json"
        logger.info(f"Salvando resultados em {results_file}")
        
        try:
            with open(results_file, "w") as f:
                json.dump(self.results, f, indent=2)
            logger.info("Resultados salvos com sucesso")
        except Exception as e:
            logger.error(f"Erro ao salvar resultados: {e}")
    
    def generate_reports(self):
        """Gera relatórios e visualizações dos resultados."""
        if not self.results:
            logger.error("Nenhum resultado para gerar relatórios.")
            return
        
        logger.info("Gerando relatórios...")
        
        # Para cada métrica, criar um gráfico comparativo
        for metric_name, metric_info in METRICS.items():
            self._generate_metric_chart(metric_name, metric_info)
        
        # Gerar relatório comparativo em formato tabular
        self._generate_markdown_report()
        
        # Gerar relatório HTML
        self.generate_html_report()
        
        logger.info(f"Relatórios gerados em {self.output_dir}")
    
    def _generate_metric_chart(self, metric_name, metric_info):
        """Gera um gráfico comparativo para uma métrica."""
        plt.figure(figsize=(12, 8))
        
        test_files = list(self.results.keys())
        tool_names = set()
        for test_file in test_files:
            tool_names.update(self.results[test_file].keys())
        
        tool_names = sorted(tool_names)
        if not tool_names:
            logger.warning(f"Nenhuma ferramenta com resultados para gerar gráfico {metric_name}")
            return
            
        x = np.arange(len(tool_names))
        width = 0.8 / len(test_files) if test_files else 0.8
        
        for i, test_file in enumerate(test_files):
            test_name = Path(test_file).stem
            values = []
            
            for tool in tool_names:
                if tool in self.results[test_file] and metric_name in self.results[test_file][tool]:
                    values.append(self.results[test_file][tool][metric_name]['mean'])
                else:
                    values.append(0)
            
            plt.bar(x + i*width - 0.4 + width/2, values, width, label=test_name)
        
        plt.xlabel('Ferramenta de Ofuscação')
        plt.ylabel(f"{metric_info['description']} ({metric_info['unit']})")
        plt.title(f"{metric_info['description']} por Ferramenta")
        plt.xticks(x, tool_names, rotation=45)
        plt.legend()
        plt.tight_layout()
        
        plt.savefig(self.output_dir / f"chart_{metric_name}.png")
        plt.close()
    
    def _generate_markdown_report(self):
        """Gera um relatório em formato Markdown."""
        report_file = self.output_dir / "benchmark_report.md"
        
        with open(report_file, "w") as f:
            f.write("# Relatório de Benchmark de Ofuscação\n\n")
            f.write("## Ferramentas Avaliadas\n\n")
            
            # Tabela de ferramentas
            f.write("| Ferramenta | Descrição |\n")
            f.write("| --- | --- |\n")
            for tool_name, tool_info in TOOLS.items():
                if tool_info.get('enabled', True):
                    f.write(f"| {tool_name} | {tool_info.get('description', 'N/A')} |\n")
            
            f.write("\n## Resultados por Arquivo de Teste\n\n")
            
            for test_file in self.results:
                test_name = Path(test_file).stem
                f.write(f"### Arquivo: {test_name}\n\n")
                
                # Para cada métrica, criar uma tabela
                for metric_name, metric_info in METRICS.items():
                    f.write(f"#### {metric_info['description']}\n\n")
                    f.write("| Ferramenta | Média | Mediana | Mínimo | Máximo | Desvio Padrão |\n")
                    f.write("| --- | --- | --- | --- | --- | --- |\n")
                    
                    for tool_name, tool_metrics in self.results[test_file].items():
                        if metric_name in tool_metrics:
                            metric = tool_metrics[metric_name]
                            f.write(f"| {tool_name} | {metric['mean']:.3f} | {metric['median']:.3f} | {metric['min']:.3f} | {metric['max']:.3f} | {metric['stdev']:.3f} |\n")
                    
                    f.write("\n")
    
    def generate_html_report(self):
        """Gera um relatório HTML com visualizações."""
        report_file = self.output_dir / "benchmark_report.html"
        
        html_content = """
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="UTF-8">
            <title>Benchmark de Ofuscação Python</title>
            <style>
                body { font-family: Arial, sans-serif; margin: 0; padding: 20px; }
                h1, h2, h3 { color: #2c3e50; }
                .container { max-width: 1200px; margin: 0 auto; }
                table { border-collapse: collapse; width: 100%; margin: 20px 0; }
                th, td { padding: 12px 15px; text-align: left; border-bottom: 1px solid #ddd; }
                th { background-color: #f2f2f2; }
                tr:hover { background-color: #f5f5f5; }
                .chart { margin: 20px 0; }
                img { max-width: 100%; }
            </style>
        </head>
        <body>
            <div class="container">
                <h1>Benchmark de Estratégias de Ofuscação Python</h1>
                
                <h2>Ferramentas Avaliadas</h2>
                <table>
                    <tr>
                        <th>Ferramenta</th>
                        <th>Descrição</th>
                    </tr>
        """
        
        # Adicionar ferramentas à tabela
        for tool_name, tool_info in TOOLS.items():
            if tool_info.get('enabled', True):
                html_content += f"""
                    <tr>
                        <td>{tool_name}</td>
                        <td>{tool_info.get('description', 'N/A')}</td>
                    </tr>
                """
        
        html_content += """
                </table>
                
                <h2>Métricas Avaliadas</h2>
                <table>
                    <tr>
                        <th>Métrica</th>
                        <th>Descrição</th>
                        <th>Unidade</th>
                    </tr>
        """
        
        # Adicionar métricas à tabela
        for metric_name, metric_info in METRICS.items():
            html_content += f"""
                    <tr>
                        <td>{metric_name}</td>
                        <td>{metric_info['description']}</td>
                        <td>{metric_info['unit']}</td>
                    </tr>
            """
        
        html_content += """
                </table>
                
                <h2>Gráficos Comparativos</h2>
        """
        
        # Adicionar gráficos
        for metric_name, metric_info in METRICS.items():
            chart_path = self.output_dir / f"chart_{metric_name}.png"
            if chart_path.exists():
                html_content += f"""
                    <div class="chart">
                        <h3>{metric_info['description']}</h3>
                        <img src="chart_{metric_name}.png" alt="Gráfico de {metric_info['description']}">
                    </div>
                """
        
        html_content += """
                <h2>Resultados Detalhados</h2>
        """
        
        # Adicionar resultados por arquivo de teste
        for test_file in self.results:
            test_name = Path(test_file).stem
            html_content += f"""
                <h3>Arquivo: {test_name}</h3>
            """
            
            # Para cada métrica, criar uma tabela
            for metric_name, metric_info in METRICS.items():
                html_content += f"""
                <h4>{metric_info['description']}</h4>
                <table>
                    <tr>
                        <th>Ferramenta</th>
                        <th>Média</th>
                        <th>Mediana</th>
                        <th>Mínimo</th>
                        <th>Máximo</th>
                        <th>Desvio Padrão</th>
                    </tr>
                """
                
                for tool_name, tool_metrics in self.results[test_file].items():
                    if metric_name in tool_metrics:
                        metric = tool_metrics[metric_name]
                        html_content += f"""
                    <tr>
                        <td>{tool_name}</td>
                        <td>{metric['mean']:.3f}</td>
                        <td>{metric['median']:.3f}</td>
                        <td>{metric['min']:.3f}</td>
                        <td>{metric['max']:.3f}</td>
                        <td>{metric['stdev']:.3f}</td>
                    </tr>
                        """
                
                html_content += """
                </table>
                """
        
        html_content += """
            </div>
        </body>
        </html>
        """
        
        with open(report_file, "w") as f:
            f.write(html_content)

    def generate_system_info_csv(self):
        """Gera um arquivo CSV com informações do sistema onde o benchmark foi executado."""
        import platform
        import psutil
        import csv
        import os
        import socket
        import datetime
        import re
        import importlib
        
        system_info_file = self.output_dir / "system_info.csv"
        logger.info(f"Gerando informações do sistema em {system_info_file}")
        
        try:
            # Coletar informações do sistema
            info = [
                ["Benchmark Date", datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")],
                ["Hostname", socket.gethostname()],
                ["OS", platform.system()],
                ["OS Version", platform.version()],
                ["OS Release", platform.release()],
                ["Architecture", platform.machine()],
                ["Python Version", platform.python_version()],
                ["Processor", platform.processor()],
                ["CPU Cores (Physical)", psutil.cpu_count(logical=False)],
                ["CPU Cores (Logical)", psutil.cpu_count(logical=True)],
                ["RAM Total (GB)", round(psutil.virtual_memory().total / (1024**3), 2)],
                ["Disk Space Total (GB)", round(psutil.disk_usage('/').total / (1024**3), 2)],
                ["Disk Space Free (GB)", round(psutil.disk_usage('/').free / (1024**3), 2)]
            ]
            
            # Coletar informações adicionais
            try:
                if hasattr(psutil, "cpu_freq"):
                    cpu_freq = psutil.cpu_freq()
                    if cpu_freq:
                        info.append(["CPU Frequency (MHz)", cpu_freq.current])
            except Exception as e:
                logger.debug(f"Não foi possível obter frequência da CPU: {e}")
            
            # Adicionar uma linha separadora antes das versões das ferramentas
            info.append(["", ""])
            info.append(["Tool Versions", ""])
                        
            # Função auxiliar para verificar versão de pacote instalado
            def get_package_version(package_name):
                try:
                    spec = importlib.util.find_spec(package_name)
                    if spec is None:
                        return None
                        
                    # Tenta importar e buscar versão
                    try:
                        module = importlib.import_module(package_name)
                        if hasattr(module, '__version__'):
                            return module.__version__
                        if hasattr(module, 'VERSION'):
                            return module.VERSION
                        if hasattr(module, 'version'):
                            return module.version
                    except:
                        pass
                    return "Instalado (versão desconhecida)"
                except:
                    return None
                    
            # Obter a versão do PyArmor (método específico)
            pyarmor_version = "Não detectado"
            try:
                # Método mais direto para PyArmor (evitar analisar output complexo)
                result = subprocess.run(
                    ["pyarmor", "version"],
                    capture_output=True,
                    text=True
                )
                if result.returncode == 0 and result.stdout:
                    # Extrair apenas a versão numérica
                    version_match = re.search(r'(\d+\.\d+\.\d+)', result.stdout)
                    if version_match:
                        pyarmor_version = version_match.group(1)
            except:
                try:
                    # Alternativa: import pyarmor diretamente
                    import pyarmor
                    if hasattr(pyarmor, '__version__'):
                        pyarmor_version = pyarmor.__version__
                except:
                    pass
            info.append(["Pyarmor Gen Version", pyarmor_version])
                    
            # Obter versão do PyMinifier
            pyminifier_version = "Não detectado"
            pkg_version = get_package_version("pyminifier")
            if pkg_version:
                pyminifier_version = pkg_version
            if pyminifier_version == "Não detectado":
                try:
                    # Tente extrair a versão a partir do conteúdo do módulo
                    import inspect
                    import pyminifier
                    source = inspect.getsource(pyminifier)
                    version_match = re.search(r'__version__\s*=\s*[\'"](\d+\.\d+\.\d+)[\'"]', source)
                    if version_match:
                        pyminifier_version = version_match.group(1)
                except:
                    pass
            info.append(["Pyminifier Version", pyminifier_version])
                
            # Obter versão do PyObfuscate (sem usar --version que gera erro)
            pyobfuscate_version = "Não detectado"
            try:
                # Método 1: verificar se o módulo está instalado
                import pyobfuscate
                if hasattr(pyobfuscate, '__version__'):
                    pyobfuscate_version = pyobfuscate.__version__
                else:
                    # Tentar extrair a versão do código-fonte
                    import inspect
                    source = inspect.getsource(pyobfuscate)
                    version_match = re.search(r'__version__\s*=\s*[\'"]([^\'"]+)[\'"]', source)
                    if version_match:
                        pyobfuscate_version = version_match.group(1)
                    else:
                        # Verificar se existe
                        pyobfuscate_version = "Instalado (versão desconhecida)"
            except:
                try:
                    # Método 2: verificar se o comando existe (sem executá-lo)
                    which_cmd = "where" if platform.system() == "Windows" else "which"
                    result = subprocess.run(
                        [which_cmd, "pyobfuscate"],
                        capture_output=True,
                        text=True
                    )
                    if result.returncode == 0 and result.stdout.strip():
                        pyobfuscate_version = "Instalado (versão desconhecida)"
                except:
                    pass
            info.append(["Pyobfuscate Version", pyobfuscate_version])
            
            # Obter versão do Cython
            cython_version = "Não detectado"
            pkg_version = get_package_version("Cython")
            if pkg_version:
                cython_version = pkg_version
            info.append(["Cython Version", cython_version])
            
            # Obter versão do PyInstaller
            pyinstaller_version = "Não detectado"
            pkg_version = get_package_version("PyInstaller")
            if pkg_version:
                pyinstaller_version = pkg_version
            if pyinstaller_version == "Não detectado":
                try:
                    result = subprocess.run(
                        ["pyinstaller", "--version"],
                        capture_output=True,
                        text=True
                    )
                    if result.returncode == 0 and result.stdout:
                        pyinstaller_version = result.stdout.strip()
                except:
                    pass
            info.append(["Pyinstaller Version", pyinstaller_version])
            
            # Escrever no arquivo CSV
            with open(system_info_file, 'w', newline='') as f:
                writer = csv.writer(f)
                writer.writerow(["Property", "Value"])
                writer.writerows(info)
                
            logger.info("Informações do sistema salvas com sucesso")
            return True
        except Exception as e:
            logger.error(f"Erro ao gerar informações do sistema: {e}")
            import traceback
            logger.error(traceback.format_exc())
            return False

def main():
    """Função principal do benchmark."""
    parser = argparse.ArgumentParser(description="Benchmark de Estratégias de Ofuscação de Código Python")
    
    parser.add_argument(
        "--test-files", "-t",
        nargs="+",
        required=True,
        help="Arquivos Python para testar com ofuscação"
    )
    
    parser.add_argument(
        "--output-dir", "-o",
        default="results",
        help="Diretório para salvar resultados (padrão: results)"
    )
    
    parser.add_argument(
        "--iterations", "-i",
        type=int,
        default=5,
        help="Número de iterações para cada teste (padrão: 5)"
    )
    
    parser.add_argument(
        "--disable-tools",
        nargs="+",
        choices=TOOLS.keys(),
        help="Desativar ferramentas específicas"
    )
    
    args = parser.parse_args()
    
    # Verificar se os arquivos de teste existem
    for test_file in args.test_files:
        if not os.path.isfile(test_file):
            logger.error(f"Arquivo de teste não encontrado: {test_file}")
            sys.exit(1)
    
    # Desativar ferramentas conforme solicitado
    if args.disable_tools:
        for tool_name in args.disable_tools:
            if tool_name in TOOLS:
                logger.info(f"Desativando ferramenta: {tool_name}")
                TOOLS[tool_name]['enabled'] = False
    
    # Executar o benchmark
    benchmark = ObfuscationBenchmark(
        test_files=args.test_files,
        output_dir=args.output_dir,
        iterations=args.iterations
    )
    
    try:
        benchmark.generate_system_info_csv()
        benchmark.run_benchmark()
        benchmark.generate_reports()
        logger.info("Benchmark concluído com sucesso!")
    except Exception as e:
        logger.error(f"Erro durante o benchmark: {e}")
        import traceback
        logger.error(traceback.format_exc())
    finally:
        benchmark.cleanup()


if __name__ == "__main__":
    main()