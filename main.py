import os
import sys
import subprocess
import shutil
import glob
from dotenv import load_dotenv

load_dotenv()

def expand_env_vars(value):
    if value is None:
        return None
    return os.path.expandvars(value)

def download_video(video_url, quality=None, output_dir=None):
    try:
        if quality is None:
            quality = os.getenv('DEFAULT_QUALITY', 'best')
        if output_dir is None:
            output_dir = expand_env_vars(os.getenv('DEFAULT_OUTPUT_DIR', './downloads'))
        
        output_dir = os.path.abspath(output_dir)
        
        if not os.path.exists(output_dir):
            os.makedirs(output_dir)
        
        yt_dlp_path = expand_env_vars(os.getenv('YT_DLP_PATH', "yt-dlp"))
        
        if not os.path.exists(yt_dlp_path):
            print(f"Erro: O executável do yt-dlp não foi encontrado em {yt_dlp_path}")
            print("Por favor, verifique se o yt-dlp está instalado corretamente.")
            return
        
        ffmpeg_path = shutil.which("ffmpeg")
        if not ffmpeg_path:
            print("AVISO: ffmpeg não encontrado no PATH. Tentando caminhos alternativos...")
            
            possible_paths = [
                "C:\\ffmpeg\\bin\\ffmpeg.exe",
                "C:\\Program Files\\ffmpeg\\bin\\ffmpeg.exe",
                "C:\\Program Files (x86)\\ffmpeg\\bin\\ffmpeg.exe",
                os.path.join(os.path.dirname(yt_dlp_path), "ffmpeg.exe"),
                os.path.join(os.path.dirname(sys.executable), "ffmpeg.exe")
            ]
            
            for path in possible_paths:
                if os.path.exists(path):
                    ffmpeg_path = path
                    print(f"FFmpeg encontrado em: {ffmpeg_path}")
                    break
            
            if not ffmpeg_path:
                print("Erro: ffmpeg não encontrado. Vamos baixar e instalar automaticamente.")
                
                try:
                    ffmpeg_dir = os.path.join(os.path.dirname(yt_dlp_path), "ffmpeg")
                    if not os.path.exists(ffmpeg_dir):
                        os.makedirs(ffmpeg_dir)
                    
                    print("Baixando FFmpeg...")
                    
                    download_command = [
                        yt_dlp_path,
                        "--extract-audio",
                        "--audio-format", "mp3",
                        "-o", os.path.join(ffmpeg_dir, "temp.%(ext)s"),
                        "https://www.youtube.com/watch?v=dQw4w9WgXcQ",
                        "--rm-cache-dir"
                    ]
                    
                    subprocess.run(download_command, capture_output=True)
                    
                    ffmpeg_path = shutil.which("ffmpeg")
                    if not ffmpeg_path:
                        ffmpeg_path = os.path.join(os.path.dirname(yt_dlp_path), "ffmpeg.exe")
                    
                    if not os.path.exists(ffmpeg_path):
                        print("Não foi possível baixar o FFmpeg automaticamente.")
                        print("Por favor, baixe e instale o FFmpeg manualmente de https://ffmpeg.org/download.html")
                        return
                    
                    print(f"FFmpeg instalado em: {ffmpeg_path}")
                    
                except Exception as e:
                    print(f"Erro ao baixar o FFmpeg: {e}")
                    print("Por favor, baixe e instale o FFmpeg manualmente de https://ffmpeg.org/download.html")
                    return
        
        if ffmpeg_path:
            print(f"Baixando vídeo para: {output_dir}")
            print(f"Qualidade selecionada: {quality}")
            
            output_template = os.path.join(output_dir, "%(title)s.%(ext)s")
            
            quality_map = {
                '720p': 'bestvideo[height<=720]+bestaudio[ext!=opus]/bestvideo[height<=720]+bestaudio',
                '1080p': 'bestvideo[height<=1080]+bestaudio[ext!=opus]/bestvideo[height<=1080]+bestaudio',
                'best': 'bestvideo+bestaudio[ext!=opus]/bestvideo+bestaudio'
            }
            
            format_option = quality_map.get(quality, quality)
            
            command = [
                yt_dlp_path,
                "-f", format_option,
                "--ffmpeg-location", ffmpeg_path,
                "--merge-output-format", "mp4",
                "--postprocessor-args", "-c:a aac -b:a 192k",
                "-o", output_template,
                video_url
            ]
            
            print("Iniciando download e mesclagem...")
            print("Comando:", " ".join(command))
            
            process = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, 
                                      universal_newlines=True, bufsize=1)
            
            for line in process.stdout:
                print(line, end='')
            
            process.wait()
            
            if process.returncode != 0:
                print("Erro ao baixar e mesclar o vídeo. Tentando método alternativo...")
            else:
                print("Download e mesclagem concluídos com sucesso!")
                
                output_files = glob.glob(os.path.join(output_dir, "*.mp4"))
                if output_files:
                    latest_file = max(output_files, key=os.path.getctime)
                    print(f"Arquivo salvo em: {latest_file}")
                    
                    print("Verificando compatibilidade com o Windows Media Player...")
                    
                    temp_file = os.path.join(output_dir, "temp_" + os.path.basename(latest_file))
                    recompress_command = [
                        ffmpeg_path,
                        "-i", latest_file,
                        "-c:v", "copy",
                        "-c:a", "aac",
                        "-b:a", "192k",
                        "-strict", "experimental",
                        temp_file
                    ]
                    
                    print("Recodificando áudio para garantir compatibilidade...")
                    recompress_process = subprocess.Popen(recompress_command, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, 
                                                        universal_newlines=True, bufsize=1)
                    
                    for line in recompress_process.stdout:
                        print(line, end='')
                    
                    recompress_process.wait()
                    
                    if recompress_process.returncode == 0:
                        os.remove(latest_file)
                        os.rename(temp_file, latest_file)
                        print(f"Arquivo recodificado com sucesso para compatibilidade com o Windows Media Player: {latest_file}")
                    else:
                        print("Aviso: Não foi possível recodificar o áudio, mas o arquivo foi baixado.")
                
                return
        
        print("Usando método alternativo (baixar separadamente e mesclar)...")
        
        print("Obtendo informações do vídeo...")
        info_command = [
            yt_dlp_path,
            "--get-filename",
            "-o", "%(title)s",
            video_url
        ]
        result = subprocess.run(info_command, capture_output=True, text=True)
        if result.returncode != 0:
            print("Erro ao obter informações do vídeo.")
            return
        
        video_title = result.stdout.strip()
        print(f"Título do vídeo: {video_title}")
        
        print(f"Baixando vídeo para: {output_dir}")
        print(f"Qualidade selecionada: {quality}")
        
        video_output = os.path.join(output_dir, f"{video_title}.video")
        audio_output = os.path.join(output_dir, f"{video_title}.audio")
        
        video_command = [
            yt_dlp_path,
            "-f", f"bestvideo[height<={quality.replace('p', '')}]" if quality.endswith('p') else "bestvideo",
            "-o", f"{video_output}.%(ext)s",
            video_url
        ]
        
        audio_command = [
            yt_dlp_path,
            "-f", "bestaudio[ext!=opus]/bestaudio",
            "-o", f"{audio_output}.%(ext)s",
            video_url
        ]
        
        print("Baixando vídeo...")
        video_process = subprocess.Popen(video_command, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, 
                                        universal_newlines=True, bufsize=1)
        
        for line in video_process.stdout:
            print(line, end='')
        
        
        video_process.wait()
        
        if video_process.returncode != 0:
            print("Erro ao baixar o vídeo.")
            return
        
        print("Baixando áudio...")
        audio_process = subprocess.Popen(audio_command, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, 
                                        universal_newlines=True, bufsize=1)
        

        for line in audio_process.stdout:
            print(line, end='')
        
    
        audio_process.wait()
        
        if audio_process.returncode != 0:
            print("Erro ao baixar o áudio.")
            return
        
        video_files = glob.glob(f"{video_output}.*")
        audio_files = glob.glob(f"{audio_output}.*")
        
        if not video_files or not audio_files:
            print("Erro: Não foi possível encontrar os arquivos baixados.")
            return
        
        video_file = video_files[0]
        audio_file = audio_files[0]
        
        print(f"Arquivo de vídeo: {video_file}")
        print(f"Arquivo de áudio: {audio_file}")
        
        if ffmpeg_path:
            print("Mesclando áudio e vídeo...")
            output_file = os.path.join(output_dir, f"{video_title}.mp4")
            
            if os.path.exists(output_file):
                os.remove(output_file)
            
            merge_command = [
                ffmpeg_path,
                "-i", video_file,
                "-i", audio_file,
                "-c:v", "copy",
                "-c:a", "aac",
                "-b:a", "192k",
                "-strict", "experimental",
                output_file
            ]
            
            print("Comando de mesclagem:", " ".join(merge_command))
            
            merge_process = subprocess.Popen(merge_command, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, 
                                           universal_newlines=True, bufsize=1)
            
            for line in merge_process.stdout:
                print(line, end='')
            
            merge_process.wait()
            
            if merge_process.returncode != 0:
                print("Erro ao mesclar os arquivos. Tentando método alternativo...")
                
                alt_merge_command = [
                    ffmpeg_path,
                    "-i", video_file,
                    "-i", audio_file,
                    "-c:v", "copy",
                    "-c:a", "aac",
                    "-b:a", "192k",
                    output_file
                ]
                
                print("Comando de mesclagem alternativo:", " ".join(alt_merge_command))
                
                alt_merge_process = subprocess.Popen(alt_merge_command, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, 
                                                  universal_newlines=True, bufsize=1)
                
                for line in alt_merge_process.stdout:
                    print(line, end='')
                
                alt_merge_process.wait()
                
                if alt_merge_process.returncode != 0:
                    print("Erro ao mesclar os arquivos com o método alternativo.")
                    print("Os arquivos de áudio e vídeo foram baixados, mas não puderam ser mesclados.")
                    print(f"Arquivos disponíveis: {video_file} e {audio_file}")
                else:
                    print(f"Mesclagem concluída com sucesso! Arquivo salvo em: {output_file}")
                    
                    try:
                        os.remove(video_file)
                        os.remove(audio_file)
                        print("Arquivos temporários removidos.")
                    except Exception as e:
                        print(f"Aviso: Não foi possível remover os arquivos temporários: {e}")
            else:
                print(f"Mesclagem concluída com sucesso! Arquivo salvo em: {output_file}")
                
                try:
                    os.remove(video_file)
                    os.remove(audio_file)
                    print("Arquivos temporários removidos.")
                except Exception as e:
                    print(f"Aviso: Não foi possível remover os arquivos temporários: {e}")
        else:
            print("Erro: FFmpeg não encontrado. Não é possível mesclar os arquivos.")
            print("Por favor, instale o FFmpeg para mesclar os arquivos automaticamente.")
            print("Os arquivos de áudio e vídeo foram baixados, mas não puderam ser mesclados.")
            print(f"Arquivos disponíveis: {video_file} e {audio_file}")
        
    except Exception as e:
        print(f"Erro ao baixar o vídeo: {e}")
        import traceback
        traceback.print_exc()

def main():
    if len(sys.argv) < 2:
        print("Uso: python main.py <URL_DO_VÍDEO> [qualidade] [diretório_de_saída]")
        print("Qualidades disponíveis: best, 720p, 1080p")
        sys.exit(1)

    video_url = sys.argv[1]
    quality = sys.argv[2] if len(sys.argv) > 2 else 'best'
    output_dir = sys.argv[3] if len(sys.argv) > 3 else './downloads'

    output_dir = output_dir.strip("'\"")

    download_video(video_url, quality, output_dir)

if __name__ == "__main__":
    main()