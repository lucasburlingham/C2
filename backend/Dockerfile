FROM python:3.11-slim
WORKDIR /app
COPY requirements.txt ./requirements.txt
RUN apt-get update && apt-get install -y --no-install-recommends \
		rtl-sdr \
		ffmpeg \
		gstreamer1.0-tools \
		gstreamer1.0-plugins-base \
		gstreamer1.0-plugins-good \
		gstreamer1.0-plugins-bad \
		gstreamer1.0-plugins-ugly \
		gstreamer1.0-libav \
	&& rm -rf /var/lib/apt/lists/* \
	&& pip install --no-cache-dir -r requirements.txt
COPY . .
CMD ["uvicorn", "backend.main:app", "--host", "0.0.0.0", "--port", "8000"]
