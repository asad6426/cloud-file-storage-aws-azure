"""REST API in front of FileService."""
from flask import Flask, Response, jsonify, request

from .service import IntegrityError, InvalidFile, from_environment


def create_app(service=None):
    app = Flask(__name__)
    app.config["MAX_CONTENT_LENGTH"] = 6 * 1024 * 1024
    service = service or from_environment()

    @app.get("/healthz")
    def healthz():
        return jsonify(status="ok", provider=service.provider)

    @app.post("/files")
    def upload():
        upload = request.files.get("file")
        if upload is None:
            return jsonify(error="Send the file in a form field named 'file'"), 400
        try:
            record = service.upload(upload.filename, upload.read(), upload.mimetype or "application/octet-stream")
        except InvalidFile as exc:
            return jsonify(error=str(exc)), 400
        return jsonify(record), 201

    @app.get("/files")
    def list_files():
        return jsonify(service.list())

    @app.get("/files/<file_id>")
    def download(file_id):
        try:
            record, data = service.download(file_id)
        except IntegrityError as exc:
            return jsonify(error=str(exc)), 502
        if record is None:
            return jsonify(error="File not found"), 404
        return Response(
            data,
            mimetype=record["content_type"],
            headers={"Content-Disposition": f'attachment; filename="{record["filename"]}"'},
        )

    return app
