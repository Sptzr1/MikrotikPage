from django.shortcuts import render, redirect
from django.conf import settings
from django.core.cache import cache
from librouteros import connect
from librouteros.query import Key
import random
from datetime import datetime, timedelta
from .models import UserPayment
from django.contrib import messages
import threading
import queue
import socket

def get_mikrotik_connection(timeout=2):
    """Intenta conectar a MikroTik con un timeout estricto."""
    result = queue.Queue()

    def connect_thread():
        try:
            # Configurar timeout para la conexión
            socket.setdefaulttimeout(timeout)
            api = connect(
                host=settings.MIKROTIK_CONFIG['host'],
                username=settings.MIKROTIK_CONFIG['username'],
                password=settings.MIKROTIK_CONFIG['password'],
                port=settings.MIKROTIK_CONFIG['port']
            )
            result.put(api)
        except Exception as e:
            result.put(None)
        finally:
            socket.setdefaulttimeout(None)

    # Crear un hilo para la conexión
    thread = threading.Thread(target=connect_thread)
    thread.daemon = True  # Hilo demonio para que se detenga si el programa termina
    thread.start()
    
    # Esperar hasta el timeout
    thread.join(timeout)
    
    if thread.is_alive():
        # Si el hilo sigue vivo, la conexión está tomando demasiado tiempo
        return None
    else:
        # Obtener el resultado de la cola
        return result.get()

def get_dummy_data():
    """Genera datos de prueba para cuando no hay conexión al Mikrotik."""
    hotspot_users = [
        {
            'name': f'usuario{i}',
            'password': f'pass{i}',
            'profile': random.choice(['default', 'vip', 'temporal']),
            'limit_uptime': f'{random.randint(1, 24)}h'
        } for i in range(1, 11)
    ]
    
    interfaces = [
        {
            'name': f'eth{i}',
            'type': random.choice(['ether', 'bridge', 'vlan']),
            'running': random.choice([True, False]),
            'mtu': random.choice([1500, 1492, 1480])
        } for i in range(1, 6)
    ]
    
    active_links = [
        {
            'user': f'usuario{random.randint(1, 10)}',
            'address': f'192.168.1.{random.randint(100, 200)}',
            'mac_address': ':'.join([f'{random.randint(0, 255):02x}' for _ in range(6)]),
            'uptime': str(timedelta(minutes=random.randint(1, 1440)))
        } for _ in range(5)
    ]
    
    queues = [
        {
            'name': f'queue{i}',
            'target': f'192.168.1.{random.randint(100, 200)}',
            'max_limit': f'{random.randint(1, 10)}M/{random.randint(1, 10)}M',
            'rate': f'{random.randint(0, 5)}M/{random.randint(0, 5)}M',
            'disabled': random.choice(['yes', 'no'])
        } for i in range(1, 6)
    ]
    
    ppp_sessions = [
        {
            'name': f'ppp_user{i}',
            'address': f'10.0.0.{random.randint(100, 200)}',
            'mac_address': ':'.join([f'{random.randint(0, 255):02x}' for _ in range(6)]),
            'uptime': str(timedelta(minutes=random.randint(1, 1440))),
            'disabled': random.choice(['yes', 'no'])
        } for i in range(1, 6)
    ]
    
    return hotspot_users, interfaces, active_links, queues, ppp_sessions

def index(request):
    """Vista para la página de inicio."""
    cache_keys = {
        'hotspot_users': 'hotspot_users_data',
        'interfaces': 'interfaces_data',
        'active_links': 'active_links_data',
        'queues': 'queues_data',
        'ppp_sessions': 'ppp_sessions_data'
    }
    
    api = get_mikrotik_connection()
    using_dummy_data = False

    if api:
        try:
            # Hotspot users
            hotspot_users = list(api.path('/ip/hotspot/user').select(Key('name'), Key('password'), Key('profile'), Key('limit-uptime')))
            for user in hotspot_users:
                if 'limit-uptime' in user:
                    user['limit_uptime'] = user.pop('limit-uptime')
            cache.set(cache_keys['hotspot_users'], hotspot_users, 300)

            # Interfaces
            interfaces = list(api.path('/interface').select(Key('name'), Key('type'), Key('running'), Key('mtu')))
            cache.set(cache_keys['interfaces'], interfaces, 300)

            # Active links
            active_links = list(api.path('/ip/hotspot/active').select(Key('user'), Key('address'), Key('mac-address'), Key('uptime')))
            for link in active_links:
                if 'mac-address' in link:
                    link['mac_address'] = link.pop('mac-address')
                try:
                    payment = UserPayment.objects.get(username=link['user'])
                    link['payment_status'] = payment.check_payment_status()
                    link['next_payment'] = payment.next_payment_date
                    link['auto_disconnect'] = payment.auto_disconnect
                    if not link['payment_status'] and payment.auto_disconnect:
                        disconnect_user(api, link['user'])
                except UserPayment.DoesNotExist:
                    link['payment_status'] = True
                    link['next_payment'] = None
                    link['auto_disconnect'] = False
            cache.set(cache_keys['active_links'], active_links, 300)

            # Queues
            queues = list(api.path('/queue/simple').select(Key('name'), Key('target'), Key('max-limit'), Key('rate'), Key('disabled')))
            for queue in queues:
                if 'max-limit' in queue:
                    queue['max_limit'] = queue.pop('max-limit')
            cache.set(cache_keys['queues'], queues, 300)

            # PPP sessions
            ppp_sessions = list(api.path('/ppp/active').select(Key('name'), Key('address'), Key('mac-address'), Key('uptime'), Key('disabled')))
            for session in ppp_sessions:
                if 'mac-address' in session:
                    session['mac_address'] = session.pop('mac-address')
            cache.set(cache_keys['ppp_sessions'], ppp_sessions, 300)

            api.close()
        except Exception as e:
            using_dummy_data = True
    else:
        using_dummy_data = True

    if using_dummy_data:
        hotspot_users, interfaces, active_links, queues, ppp_sessions = get_dummy_data()
        for link in active_links:
            link['payment_status'] = random.choice([True, False])
            link['next_payment'] = (datetime.now() + timedelta(days=random.randint(-10, 30))).date()
            link['auto_disconnect'] = random.choice([True, False])
        cache.set(cache_keys['hotspot_users'], hotspot_users, 300)
        cache.set(cache_keys['interfaces'], interfaces, 300)
        cache.set(cache_keys['active_links'], active_links, 300)
        cache.set(cache_keys['queues'], queues, 300)
        cache.set(cache_keys['ppp_sessions'], ppp_sessions, 300)

    return render(request, 'dashboard/index.html')

def hotspot_users(request):
    """Vista para listar usuarios Hotspot."""
    context = {}
    cache_key = 'hotspot_users_data'
    hotspot_users = None
    api = get_mikrotik_connection()

    if api:
        try:
            hotspot_users = list(api.path('/ip/hotspot/user').select(Key('name'), Key('password'), Key('profile'), Key('limit-uptime')))
            for user in hotspot_users:
                if 'limit-uptime' in user:
                    user['limit_uptime'] = user.pop('limit-uptime')
            cache.set(cache_key, hotspot_users, 300)
        except Exception as e:
            context['error'] = str(e)
            hotspot_users = cache.get(cache_key)
            if hotspot_users is None:
                hotspot_users = get_dummy_data()[0]
                context['warning'] = '⚠️ Se están utilizando datos de prueba. No se pudo conectar al Mikrotik.'
            else:
                context['warning'] = '⚠️ Pérdida de conexión con el router. Mostrando datos en caché.'
        api.close()
    else:
        hotspot_users = cache.get(cache_key)
        if hotspot_users is None:
            hotspot_users = get_dummy_data()[0]
            context['warning'] = '⚠️ Se están utilizando datos de prueba. No se pudo conectar al Mikrotik.'
        else:
            context['warning'] = '⚠️ Pérdida de conexión con el router. Mostrando datos en caché.'

    context['hotspot_users'] = hotspot_users
    return render(request, 'dashboard/hotspot_users/index.html', context)

def interfaces(request):
    """Vista para listar interfaces."""
    context = {}
    cache_key = 'interfaces_data'
    interfaces = None
    api = get_mikrotik_connection()

    if api:
        try:
            interfaces = list(api.path('/interface').select(Key('name'), Key('type'), Key('running'), Key('mtu')))
            cache.set(cache_key, interfaces, 300)
        except Exception as e:
            context['error'] = str(e)
            interfaces = cache.get(cache_key)
            if interfaces is None:
                interfaces = get_dummy_data()[1]
                context['warning'] = '⚠️ Se están utilizando datos de prueba. No se pudo conectar al Mikrotik.'
            else:
                context['warning'] = '⚠️ Pérdida de conexión con el router. Mostrando datos en caché.'
        api.close()
    else:
        interfaces = cache.get(cache_key)
        if interfaces is None:
            interfaces = get_dummy_data()[1]
            context['warning'] = '⚠️ Se están utilizando datos de prueba. No se pudo conectar al Mikrotik.'
        else:
            context['warning'] = '⚠️ Pérdida de conexión con el router. Mostrando datos en caché.'

    context['interfaces'] = interfaces
    return render(request, 'dashboard/interfaces/index.html', context)

def active_links(request):
    """Vista para listar enlaces activos."""
    context = {}
    cache_key = 'active_links_data'
    active_links = None
    api = get_mikrotik_connection()

    if api:
        try:
            active_links = list(api.path('/ip/hotspot/active').select(Key('user'), Key('address'), Key('mac-address'), Key('uptime')))
            for link in active_links:
                if 'mac-address' in link:
                    link['mac_address'] = link.pop('mac-address')
                try:
                    payment = UserPayment.objects.get(username=link['user'])
                    link['payment_status'] = payment.check_payment_status()
                    link['next_payment'] = payment.next_payment_date
                    link['auto_disconnect'] = payment.auto_disconnect
                    if not link['payment_status'] and payment.auto_disconnect:
                        disconnect_user(api, link['user'])
                except UserPayment.DoesNotExist:
                    link['payment_status'] = True
                    link['next_payment'] = None
                    link['auto_disconnect'] = False
            cache.set(cache_key, active_links, 300)
        except Exception as e:
            context['error'] = str(e)
            active_links = cache.get(cache_key)
            if active_links is None:
                active_links = get_dummy_data()[2]
                for link in active_links:
                    link['payment_status'] = random.choice([True, False])
                    link['next_payment'] = (datetime.now() + timedelta(days=random.randint(-10, 30))).date()
                    link['auto_disconnect'] = random.choice([True, False])
                context['warning'] = '⚠️ Se están utilizando datos de prueba. No se pudo conectar al Mikrotik.'
            else:
                context['warning'] = '⚠️ Pérdida de conexión con el router. Mostrando datos en caché.'
        api.close()
    else:
        active_links = cache.get(cache_key)
        if active_links is None:
            active_links = get_dummy_data()[2]
            for link in active_links:
                link['payment_status'] = random.choice([True, False])
                link['next_payment'] = (datetime.now() + timedelta(days=random.randint(-10, 30))).date()
                link['auto_disconnect'] = random.choice([True, False])
            context['warning'] = '⚠️ Se están utilizando datos de prueba. No se pudo conectar al Mikrotik.'
        else:
            context['warning'] = '⚠️ Pérdida de conexión con el router. Mostrando datos en caché.'

    context['active_links'] = active_links
    return render(request, 'dashboard/active_links/index.html', context)

def queues(request):
    """Vista para listar queues."""
    context = {}
    cache_key = 'queues_data'
    queues = None
    api = get_mikrotik_connection()

    if api:
        try:
            queues = list(api.path('/queue/simple').select(Key('name'), Key('target'), Key('max-limit'), Key('rate'), Key('disabled')))
            for queue in queues:
                if 'max-limit' in queue:
                    queue['max_limit'] = queue.pop('max-limit')
            cache.set(cache_key, queues, 300)
        except Exception as e:
            context['error'] = str(e)
            queues = cache.get(cache_key)
            if queues is None:
                queues = get_dummy_data()[3]
                context['warning'] = '⚠️ Se están utilizando datos de prueba. No se pudo conectar al Mikrotik.'
            else:
                context['warning'] = '⚠️ Pérdida de conexión con el router. Mostrando datos en caché.'
        api.close()
    else:
        queues = cache.get(cache_key)
        if queues is None:
            queues = get_dummy_data()[3]
            context['warning'] = '⚠️ Se están utilizando datos de prueba. No se pudo conectar al Mikrotik.'
        else:
            context['warning'] = '⚠️ Pérdida de conexión con el router. Mostrando datos en caché.'

    context['queues'] = queues
    return render(request, 'dashboard/queues/index.html', context)

def list_ppp_sessions(request):
    """Vista para listar sesiones PPP activas."""
    context = {}
    cache_key = 'ppp_sessions_data'
    ppp_sessions = None
    api = get_mikrotik_connection()

    if api:
        try:
            ppp_sessions = list(api.path('/ppp/active').select(Key('name'), Key('address'), Key('mac-address'), Key('uptime'), Key('disabled')))
            for session in ppp_sessions:
                if 'mac-address' in session:
                    session['mac_address'] = session.pop('mac-address')
            cache.set(cache_key, ppp_sessions, 300)
        except Exception as e:
            context['error'] = str(e)
            ppp_sessions = cache.get(cache_key)
            if ppp_sessions is None:
                ppp_sessions = get_dummy_data()[4]
                context['warning'] = '⚠️ Se están utilizando datos de prueba. No se pudo conectar al Mikrotik.'
            else:
                context['warning'] = '⚠️ Pérdida de conexión con el router. Mostrando datos en caché.'
        api.close()
    else:
        ppp_sessions = cache.get(cache_key)
        if ppp_sessions is None:
            ppp_sessions = get_dummy_data()[4]
            context['warning'] = '⚠️ Se están utilizando datos de prueba. No se pudo conectar al Mikrotik.'
        else:
            context['warning'] = '⚠️ Pérdida de conexión con el router. Mostrando datos en caché.'

    context['ppp_sessions'] = ppp_sessions
    return render(request, 'dashboard/ppp_sessions/index.html', context)

def disconnect_user(api, username):
    """Desconecta un usuario del hotspot."""
    try:
        active_users = list(api.path('/ip/hotspot/active').select())
        for user in active_users:
            if user.get('user') == username:
                api.path('/ip/hotspot/active').remove(user.get('.id'))
                cache.delete('active_links_data')  # Invalidar caché de enlaces activos
                return True
        return False
    except Exception as e:
        return False

def disconnect_user_view(request, username):
    """Vista para desconectar un usuario."""
    api = get_mikrotik_connection()
    if api:
        if disconnect_user(api, username):
            messages.success(request, f'Usuario {username} desconectado exitosamente')
        else:
            messages.error(request, f'No se pudo desconectar al usuario {username}')
        api.close()
    else:
        try:
            payment = UserPayment.objects.get(username=username)
            payment.is_active = not payment.is_active
            payment.save()
            status = "desconectado" if not payment.is_active else "conectado"
            messages.info(request, f'Estado del usuario {username} actualizado a {status} (sin conexión al Mikrotik)')
        except UserPayment.DoesNotExist:
            messages.error(request, f'No se encontró el usuario {username}')
    return redirect('active_links')

def toggle_auto_disconnect(request, username):
    """Vista para activar/desactivar desconexión automática."""
    try:
        payment = UserPayment.objects.get(username=username)
        payment.auto_disconnect = not payment.auto_disconnect
        payment.save()
        messages.success(request, f'Desconexión automática {"activada" if payment.auto_disconnect else "desactivada"} para {username}')
        cache.delete('active_links_data')  # Invalidar caché para reflejar cambios
    except UserPayment.DoesNotExist:
        messages.error(request, f'No se encontró el usuario {username}')
    return redirect('active_links')

def enable_queue(request, queue_name):
    """Activa una Queue en MikroTik."""
    api = get_mikrotik_connection()
    if api:
        try:
            queue_id = next(
                (q['.id'] for q in api.path('/queue/simple').select() if q.get('name') == queue_name), None
            )
            if queue_id:
                api.path('/queue/simple').update(**{'.id': queue_id, 'disabled': 'no'})
                messages.success(request, f'Queue {queue_name} activada correctamente')
                cache.delete('queues_data')  # Invalidar caché
            else:
                messages.error(request, f'No se encontró la Queue {queue_name}')
        except Exception as e:
            messages.error(request, f'Error al activar la queue: {str(e)}')
        api.close()
    return redirect('queues')

def disable_queue(request, queue_name):
    """Desactiva una Queue en MikroTik."""
    api = get_mikrotik_connection()
    if api:
        try:
            queue_id = next(
                (q['.id'] for q in api.path('/queue/simple').select() if q.get('name') == queue_name), None
            )
            if queue_id:
                api.path('/queue/simple').update(**{'.id': queue_id, 'disabled': 'yes'})
                messages.success(request, f'Queue {queue_name} desactivada correctamente')
                cache.delete('queues_data')  # Invalidar caché
            else:
                messages.error(request, f'No se encontró la Queue {queue_name}')
        except Exception as e:
            messages.error(request, f'Error al desactivar la queue: {str(e)}')
        api.close()
    return redirect('queues')

def delete_queue(request, queue_name):
    """Elimina una Queue en MikroTik."""
    api = get_mikrotik_connection()
    if api:
        try:
            queue_id = next(
                (q['.id'] for q in api.path('/queue/simple').select() if q.get('name') == queue_name), None
            )
            if queue_id:
                api.path('/queue/simple').remove(queue_id)
                messages.success(request, f'Queue {queue_name} eliminada correctamente')
                cache.delete('queues_data')  # Invalidar caché
            else:
                messages.error(request, f'No se encontró la Queue {queue_name}')
        except Exception as e:
            messages.error(request, f'Error al eliminar la queue: {str(e)}')
        api.close()
    return redirect('queues')

def disconnect_ppp(request, ppp_name):
    """Desconecta una sesión PPP activa."""
    api = get_mikrotik_connection()
    if api:
        try:
            ppp_id = next((s['.id'] for s in api.path('/ppp/active').select() if s.get('name') == ppp_name), None)
            if ppp_id:
                api.path('/ppp/active').remove(ppp_id)
                messages.success(request, f'Sesión PPP {ppp_name} desconectada correctamente')
                cache.delete('ppp_sessions_data')  # Invalidar caché
            else:
                messages.error(request, f'No se encontró la sesión PPP {ppp_name}')
        except Exception as e:
            messages.error(request, f'Error al desconectar la sesión PPP: {str(e)}')
        api.close()
    return redirect('ppp_sessions')

def delete_ppp(request, ppp_name):
    """Elimina un usuario PPP de MikroTik."""
    api = get_mikrotik_connection()
    if api:
        try:
            ppp_secret_id = next((s['.id'] for s in api.path('/ppp/secret').select() if s.get('name') == ppp_name), None)
            if ppp_secret_id:
                api.path('/ppp/secret').remove(ppp_secret_id)
                messages.success(request, f'Usuario PPP {ppp_name} eliminado correctamente')
                cache.delete('ppp_sessions_data')  # Invalidar caché
            else:
                messages.error(request, f'No se encontró el usuario PPP {ppp_name}')
        except Exception as e:
            messages.error(request, f'Error al eliminar el usuario PPP: {str(e)}')
        api.close()
    return redirect('ppp_sessions')