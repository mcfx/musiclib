from minio import Minio
import config

minioClient = Minio(config.MINIO_ADDR, access_key = config.MINIO_ACCESS_KEY, secret_key = config.MINIO_SECRET_KEY)

def get_object(object_name):
	return minioClient.get_object(config.MINIO_BUCKET, object_name).data

def fget_object(object_name, file_path):
	return minioClient.fget_object(config.MINIO_BUCKET, object_name, file_path)

def put_object(object_name, data, length):
	return minioClient.put_object(config.MINIO_BUCKET, object_name, data, length)

def fput_object(object_name, file_path):
	return minioClient.fput_object(config.MINIO_BUCKET, object_name, file_path)

def stat_object(object_name):
	return minioClient.stat_object(config.MINIO_BUCKET, object_name)

def presigned_get_object(object_name, expires, response_headers = {}):
	return minioClient.presigned_get_object(config.MINIO_BUCKET, object_name, expires, response_headers)
