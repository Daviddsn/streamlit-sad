# Cursos da UFS

Painel Streamlit do catálogo de cursos da UFS. Cada linha do CSV é uma oferta.

## EasyPanel

1. Crie um serviço do tipo **App**.
2. Aponte a fonte para este diretório (Git ou upload).
3. Build: **Dockerfile** (não use Nixpacks).
4. Porta do contêiner: **8501**. Se o painel definir a variável `PORT`, o processo escuta nela.
5. Domínio em HTTPS. O proxy do EasyPanel precisa encaminhar WebSocket; o servidor já sobe com CORS e XSRF desligados para funcionar atrás desse proxy.
6. Health check: `/_stcore/health`.

O CSV vai dentro da imagem. Para trocar o extrato, substitua `cur-csv-cursos-da-ufs.csv` e faça um novo deploy.

## Local

```bash
pip install -r requirements.txt
streamlit run app.py
```
