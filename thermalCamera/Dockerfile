FROM registry.fedoraproject.org/fedora:38

RUN dnf install -y \
https://download1.rpmfusion.org/free/fedora/rpmfusion-free-release-38.noarch.rpm \
https://download1.rpmfusion.org/nonfree/fedora/rpmfusion-nonfree-release-38.noarch.rpm

RUN dnf install  -y ffmpeg python3 python3-pip && ln -s /usr/bin/python3 /usr/bin/python

WORKDIR /app

COPY python/ .

RUN pip install --no-cache-dir -r requirements.txt

ENV RTSP_URL=rtsp://192.168.1.144:8554/mjpeg/1
ENV T_LITE_URL=http://192.168.1.145/json
ENV X_OFFSET=0
ENV Y_OFFSET=0
ENV ALPHA=0.6

ARG user=appuser
ARG group=appuser
ARG uid=1000
ARG gid=1000
RUN groupadd -g ${gid} ${group} && \
	useradd -u ${uid} -g ${group} ${user} && \
	chown -R ${uid}:${gid} /app
    
RUN chmod -R 777 /app

EXPOSE 4000

USER ${uid}:${gid}

CMD [ "python", "/app/thermalOverlay.py" ]
