FROM python:3.13-slim
WORKDIR /srv
COPY requirements.in .
RUN pip install --no-cache-dir -r requirements.in
COPY app.py stlmodel.py ./
COPY web ./web
ENV UPLOAD_DIR=/data/uploads PORT=8765
VOLUME /data
EXPOSE 8765
HEALTHCHECK CMD python -c "import urllib.request as u; u.urlopen('http://127.0.0.1:8765/healthz')"
CMD ["python", "app.py"]
