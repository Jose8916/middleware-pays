FROM library/python:3.8-alpine

# Install requirements and libraries.
#   --no-cache allows users to install packages with an index that is updated and used on-the-fly and not cached locally
RUN apk update \
    && apk --no-cache --quiet add gcc make g++ bash git openssh \
    postgresql-dev curl build-base libffi-dev python3-dev py-pip \
    jpeg-dev zlib-dev libsass-dev \
    && pip install --upgrade pip \
    && apk add --no-cache geos gdal

# RUN mkdir /app
COPY . ./app/
WORKDIR /app

COPY requirements.txt .
RUN pip install -r requirements.txt

EXPOSE 8000
# CMD ["python", "manage.py", "runserver", "0.0.0.0:8000"]
