from django.db import models


class UserManager(models.Manager):
	def create_user(self, username, password, email):
		res = self.create(username=username, password=password, email=email)
		return res


class User(models.Model):
	username = models.CharField(max_length=32, primary_key=True)
	password = models.CharField(max_length=32)
	email = models.CharField(max_length=64)
	objects = UserManager()
