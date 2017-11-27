from django.db import models
from django.db.models.deletion import CASCADE
import time


def mode_days(days_count):
	return 'days-' + days_count


def time_ticks():
	return int(round(time.time() * 1000))


class EventManager(models.Manager):
	def create_event(self, user, day, start_time, length, category_id, is_active=True, event_name='', event_note=''):
		res = self.create(
			event_id=time_ticks(),
			user=user,
			day=day,
			start_time=start_time,
			length=length,
			is_active=is_active,
			event_name=event_name,
			event_note=event_note,
			category_id=category_id
		)
		return res


class Event(models.Model):
	# the time tick when event created is the event id
	event_id = models.BigIntegerField(primary_key=True, default=0)
	user = models.ForeignKey('users.User', on_delete=CASCADE)
	# format: 6-5-4-3-2-1-0 representing sun-mon-tue-wed-thu-fri-sat
	day = models.SmallIntegerField()
	# format: (dynamic on MODE_SINGLE)yymmddhhmm, (static on MODE_REPEAT)hhmm
	start_time = models.IntegerField()
	# in minutes, and only multiple of 30min
	length = models.SmallIntegerField(default=30)
	is_active = models.BooleanField(default=True)
	event_name = models.CharField(max_length=32, default='')
	event_note = models.CharField(max_length=200, default='')
	category_id = models.IntegerField()
	objects = EventManager()

	@staticmethod
	def max_event_length():
		return 240  # 240 minutes = 4 hours

	def __json__(self):
		return {
			'event_id': self.event_id,
			'username': self.user.username,
			'day': self.day,
			'start_time': self.start_time,
			'length': self.length,
			'event_name': self.event_name,
			'event_note': self.event_note,
			'category_id': self.category_id
		}
