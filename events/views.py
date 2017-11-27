import json
import random

import ai_core
from ai_core import Tools, CategoryAdvisor

from django.core.exceptions import ObjectDoesNotExist
from rest_framework.decorators import api_view
from rest_framework.response import Response as Res
from events.models import Event
from users.views import is_user_valid, RES_BAD_REQUEST, RES_SUCCESS, RES_FAILURE

from users.models import User


def overlaps(user, start_time, length):
	# lvl1 - start-time check
	if Event.objects.filter(user=user, is_active=True, start_time__range=(start_time, Tools.time_add(start_time, length) - 1)).exists():
		return True

	# lvl2 - running events check (at the time instance)
	for event in Event.objects.filter(user=user, is_active=True, start_time__range=(start_time - int(Event.max_event_length() / 60), start_time - 1)):
		if Tools.time_add(event.start_time, event.length) > start_time:
			return True

	return False


@api_view(['POST'])
def flushdb(request):
	req_body = request.body.decode('utf-8')
	json_body = json.loads(req_body)

	if 'data' in json_body:
		if 'user' in json_body['data']:
			User.objects.all().delete()
		if 'event' in json_body['data']:
			Event.objects.all().delete()
		return Res(data={'result': 'all done'})
	else:
		return Res(data={'result': 'failed'})


@api_view(['GET', 'POST'])
def get_categorycodes(request):
	arr = []
	for category in Tools.cat_map:
		arr.append({category['name']: category['id']})
	return Res(data={'result': RES_SUCCESS, 'categories': arr})


@api_view(['GET', 'POST'])
def get_constants(request):
	return Res(data={'result': RES_SUCCESS, 'event_max_length': Event.max_event_length()})


@api_view(['POST'])
def get_suggestion(request):
	req_body = request.body.decode('utf-8')
	json_body = json.loads(req_body)
	if 'username' in json_body and 'password' in json_body and is_user_valid(json_body['username'], json_body['password']) and 'category_id' in json_body:
		user = User.objects.get(username=json_body['username'])
		category_id = json_body['category_id']

		# detect batch/single-user suggestion mode
		if 'users' in json_body:
			# group suggestion
			try:
				temp_advisors = [ai_core.advisors[User.objects.get(username=username)][category_id] for username in json_body['users']]
				temp_advisors += [ai_core.advisors[user][category_id]]

				dataset_hr = []
				dataset_dy = []

				for arr in [advisor.dataset_hr['input'] for advisor in temp_advisors]:
					for part in arr:
						dataset_hr += [int(x) for x in part]
				for arr in [advisor.dataset_dy['input'] for advisor in temp_advisors]:
					for part in arr:
						dataset_dy += [int(x) for x in part]

				advisor = CategoryAdvisor.create(user=user, category_id=category_id)
				advisor.OBSERVE_LENGTH *= len(json_body['users']) + 1
				advisor.retrain_complete(cmp_history_hr=dataset_hr, cmp_history_dy=dataset_dy)
				suggestion = advisor.suggest_int()

				return Res(data={'result': RES_SUCCESS, 'suggested_time': suggestion})
			except ObjectDoesNotExist:
				return Res(data={'result': RES_BAD_REQUEST})
		else:
			# single user suggetion
			suggestion = ai_core.request_suggestion(user=user, category_id=category_id)
			return Res(data={'result': RES_SUCCESS, 'suggested_time': suggestion})
	else:
		return Res(data={'result': RES_BAD_REQUEST})


@api_view(['POST'])
def get_event_by_id(request):
	req_body = request.body.decode('utf-8')
	json_body = json.loads(req_body)
	if 'username' in json_body and 'password' in json_body and is_user_valid(json_body['username'], json_body['password']) and 'event_id' in json_body:
		user = User.objects.get(username=json_body['username'])
		if Event.objects.filter(user=user, is_active=True, event_id=json_body['event_id']).exists():
			return Res(data={'result': RES_BAD_REQUEST, 'event': Event.objects.get(user=user, is_active=True, event_id=json_body['event_id']).__json__()})
		else:
			return Res(data={'result': RES_FAILURE})
	else:
		return Res(data={'result': RES_BAD_REQUEST})


@api_view(['POST'])
def check_periodfree(request):
	req_body = request.body.decode('utf-8')
	json_body = json.loads(req_body)
	if 'username' in json_body and 'password' in json_body and is_user_valid(json_body['username'], json_body['password']) and 'start_time' in json_body and 'length' in json_body:
		user = User.objects.get(username=json_body['username'])
		return Res(data={'result': RES_SUCCESS if not overlaps(user, json_body['start_time'], json_body['length']) else RES_FAILURE})
	else:
		return Res(data={'result': RES_BAD_REQUEST})


@api_view(['POST'])
def get_events(request):
	req_body = request.body.decode('utf-8')
	json_body = json.loads(req_body)

	if 'username' in json_body and 'password' in json_body and is_user_valid(json_body['username'], json_body['password']):
		user = User.objects.get(username=json_body['username'])

		_from = json_body['period_from']
		_till = json_body['period_till']

		result = {}
		array = []

		# lvl1 events that start in the specified period
		for event in Event.objects.filter(user=user, is_active=True, start_time__range=(_from, _till - 1)):
			array.append(event.__json__())

		# lvl2 events that are started before specified period and overlaps the period
		for event in Event.objects.filter(user=user, start_time__range=(Tools.time_add(_from, -Event.max_event_length()), _from - 1)):
			if Tools.time_add(event.start_time, event.length) > _from:
				array.append(event.__json__())

		result['result'] = RES_SUCCESS
		result['array'] = array
		return Res(data=result)
	return Res(data={'result': RES_BAD_REQUEST})


@api_view(['POST'])
def create_event(request):
	req_body = request.body.decode('utf-8')
	json_body = json.loads(req_body)

	if 'username' in json_body and 'password' in json_body and is_user_valid(json_body['username'], json_body['password']):
		user = User.objects.get(username=json_body['username'])
		if 'event_id' in json_body and Event.objects.filter(event_id=json_body['event_id'], is_active=True).exists():
			# edit the existing event
			event = Event.objects.get(event_id=json_body['event_id'], is_active=True)

			event.user = user
			event.day = json_body['day'] if 'day' in json_body else event.day
			event.start_time = json_body['start_time'] if 'start_time' in json_body else event.start_time
			event.length = json_body['length'] if 'length' in json_body else event.length
			event.event_name = json_body['event_name'] if 'event_name' in json_body else event.event_name
			event.event_note = json_body['event_note'] if 'event_note' in json_body else event.event_note
			event.category_id = json_body['category_id'] if 'category_id' in json_body else event.category_id
			event.save()

			ai_core.check_retrain(user=user)
			return Res(data={'result': RES_SUCCESS, 'event_id': event.event_id})
		else:
			# create new event
			if 'users' in json_body:
				# batch create mode
				users = [user]
				event_ids = []
				rollback = False
				for username in json_body['users']:
					users.append(User.objects.get(username=username))
				for user in users:
					if overlaps(user, json_body['start_time'], json_body['length']):
						rollback = True
						break
					event = Event.objects.create_event(
						user=user,
						day=json_body['day'],
						start_time=json_body['start_time'],
						length=json_body['length'],
						is_active=True,
						event_name='' if 'event_name' not in json_body else json_body['event_name'],
						event_note='' if 'event_note' not in json_body else json_body['event_note'],
						category_id=json_body['category_id']
					)
					event_ids.append(event.event_id)
				if rollback:
					for event_id in event_ids:
						Event.objects.get(event_id=event_id).delete()
					return Res(data={'result': RES_FAILURE})
				else:
					ai_core.check_retrain(user=User.objects.get(username=json_body['username']))
					return Res(data={'result': RES_SUCCESS, 'event_ids': event_ids})
			else:
				# single-user mode
				if overlaps(user, json_body['start_time'], json_body['length']):
					return Res(data={'result': RES_FAILURE})
				event = Event.objects.create_event(
					user=user,
					day=json_body['day'],
					start_time=json_body['start_time'],
					length=json_body['length'],
					is_active=True,
					event_name='' if 'event_name' not in json_body else json_body['event_name'],
					event_note='' if 'event_note' not in json_body else json_body['event_note'],
					category_id=json_body['category_id']
				)
				return Res(data={'result': RES_SUCCESS, 'event_id': event.event_id})
	else:
		return Res(data={'result': RES_BAD_REQUEST})


@api_view(['POST'])
def disable_event(request):
	req_body = request.body.decode('utf-8')
	json_body = json.loads(req_body)
	if 'username' in json_body and 'password' in json_body and is_user_valid(json_body['username'], json_body['password']):
		user = User.objects.filter(username=json_body['username'])

		if Event.objects.filter(user=user, event_id=json_body['event_id']).exists():
			event = Event.objects.filter(user=user, event_id=json_body['event_id'])[0]
			if event and event.is_active:
				event.is_active = False
				event.save()
				return Res(data={'result': RES_SUCCESS})
			else:
				return Res(data={'result': RES_FAILURE})
		else:
			return Res(data={'result': RES_FAILURE})
	else:
		return Res(data={'result': RES_BAD_REQUEST})


@api_view(['POST'])
def populate(request):
	req_body = request.body.decode('utf-8')
	json_body = json.loads(req_body)

	if 'username' in json_body and 'password' in json_body and is_user_valid(json_body['username'], json_body['password']):
		user = User.objects.filter(username=json_body['username'])

		if 'size' in json_body:
			obj_count = Event.objects.filter(user=user).count()

			for category in Tools.cat_map:
				# calculate randomly
				day = category['day'] + random.randrange(-1, 2, 1)
				start_time = category['time'] + random.randrange(-1, 2, 1)

				# verify validity of random calculation
				start_time = start_time if 0 < start_time < 24 else category['start_time']
				day = day if 0 <= day < 7 else category['day']

				for n in range(json_body['size']):
					Event.objects.create_event(user=user, day=day, start_time=start_time, length=60, category_id=category['id'], is_active=False)

			return Res(data={'result': RES_SUCCESS, 'populated': '%d new hidden events' % (Event.objects.filter(user=user).count() - obj_count)})
		else:
			return Res(data={'result': RES_BAD_REQUEST})
	else:
		return Res(data={'result': RES_BAD_REQUEST})
