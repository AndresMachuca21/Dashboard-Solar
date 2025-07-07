from ftplib import FTP
import os

# ==== 🔐 CREDENCIALES DEL FTP ====
ftp_host = 
ftp_user = 
ftp_pass = 
ftp_port = 
ftp_dir = 
local_path = 


try:
    # Crear carpeta si no existe
    os.makedirs(os.path.dirname(local_path), exist_ok=True)

    # Conectar al FTP
    ftp = FTP()
    ftp.connect(ftp_host, ftp_port)
    ftp.login(ftp_user, ftp_pass)
    ftp.cwd(ftp_dir)

    # Buscar archivos .csv
    archivos = ftp.nlst()
    archivos_csv = [f for f in archivos if f.endswith(".csv")]
    if not archivos_csv:
        print("No hay archivos CSV en el FTP.")
    else:
        # Elegir el más reciente (alfabéticamente)
        archivo_reciente = sorted(archivos_csv)[-1]
        print(f"Descargando: {archivo_reciente}")

        # Eliminar archivo anterior si existe
        if os.path.exists(local_path):
            os.remove(local_path)

        # Descargar con nombre fijo
        with open(local_path, "wb") as f:
            ftp.retrbinary(f"RETR {archivo_reciente}", f.write)

        print(f"Archivo guardado como: {local_path}")

    ftp.quit()

except Exception as e:
    print(f"Error al conectar o descargar desde el FTP: {e}")
