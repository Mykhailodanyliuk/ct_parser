FROM python:latest

SHELL ["/bin/bash", "-c"]

ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFERED 1

RUN pip install --upgrade pip

RUN apt update && apt -qy install gcc libjpeg-dev libxslt-dev \
    libpq-dev libmariadb-dev libmariadb-dev-compat gettext cron openssh-client \
    flake8 locales vim

RUN useradd -rms /bin/bash user && chmod 777 /opt /run

WORKDIR /ct_parser

COPY --chown=user:user . .

RUN chown -R user:user /ct_parser

RUN pip install -r requirements.txt

USER user

CMD ["python", "clinical_trials_uploader.py"]