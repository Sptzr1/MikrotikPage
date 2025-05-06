from django.shortcuts import render, redirect
from django.conf import settings
from librouteros import connect
from librouteros.query import Key
import random
from datetime import datetime, timedelta
from .models import UserPayment
from django.contrib import messages

def get_dummy_data():

    """Genera datos de prueba para cuando no hay conexión al Mikrotik"""
    # Datos dummy para usuarios hotspot
    hotspot_users = [
        {
            'name': f'usuario{i}',
            'password': f'pass{i}',
            'profile': random.choice(['default', 'vip', 'temporal']),
            'limit_uptime': f'{random.randint(1, 24)}h'
        } for i in range(1, 11)
    ]
    
    # Datos dummy para interfaces
    interfaces = [
        {
            'name': f'eth{i}',
            'type': random.choice(['ether', 'bridge', 'vlan']),
            'running': random.choice([True, False]),
            'mtu': random.choice([1500, 1492, 1480])
        } for i in range(1, 6)
    ]
    
    # Datos dummy para enlaces activos
    active_links = [
        {
            'user': f'usuario{random.randint(1, 10)}',
            'address': f'192.168.1.{random.randint(100, 200)}',
            'mac_address': ':'.join([f'{random.randint(0, 255):02x}' for _ in range(6)]),
            'uptime': str(timedelta(minutes=random.randint(1, 1440)))
        } for _ in range(5)
    ]
    
    return hotspot_users, interfaces, active_links

def delete_queue(request, queue_name):
    """Elimina una Queue en MikroTik"""
    api = get_mikrotik_connection()
    if api:
        try:
            queue_id = next(
                (q['.id'] for q in api.path('/queue/simple').select() if q.get('name') == queue_name), None
            )
            if queue_id:
                api.path('/queue/simple').remove(queue_id)  # 🔹 Elimina la queue
                messages.success(request, f'Queue {queue_name} eliminada correctamente')
            else:
                messages.error(request, f'No se encontró la Queue {queue_name}')
        except Exception as e:
            messages.error(request, f'Error al eliminar la queue: {str(e)}')
        api.close()
    return redirect('index')
    
def enable_queue(request, queue_name):
    """Activa una Queue en MikroTik"""
    api = get_mikrotik_connection()
    if api:
        try:
            queue_id = next(
                (q['.id'] for q in api.path('/queue/simple').select() if q.get('name') == queue_name), None
            )
            if queue_id:
                api.path('/queue/simple').update(**{'.id': queue_id, 'disabled': 'no'})  # 🔹 Activa la queue
                messages.success(request, f'Queue {queue_name} activada correctamente')
            else:
                messages.error(request, f'No se encontró la Queue {queue_name}')
        except Exception as e:
            messages.error(request, f'Error al activar la queue: {str(e)}')
        api.close()
    return redirect('index')

def disable_queue(request, queue_name):
    """Desactiva una Queue en MikroTik"""
    api = get_mikrotik_connection()
    if api:
        try:
            queue_id = list(api.path('/queue/simple').select())[0]['.id']  # Encuentra el ID de la queue
            # Desactiva la queue
            api.path('/queue/simple').update(**{'.id': queue_id, 'disabled': 'yes'})
            messages.success(request, f'Queue {queue_name} desactivada correctamente')
        except Exception as e:
            messages.error(request, f'Error al desactivar la queue: {str(e)}')
        api.close()
    return redirect('index')

def list_ppp_sessions(request):
    """Obtiene todas las sesiones PPP activas"""
    context = {}
    api = get_mikrotik_connection()
    
    ppp_sessions = []
    if api:
        try:
            ppp_sessions = list(api.path('/ppp/active').select())
            for session in ppp_sessions:
                if 'mac-address' in session:
                    session['mac_address'] = session.pop('mac-address')
        except Exception as e:
            context['error'] = str(e)
        api.close()

    context['ppp_sessions'] = ppp_sessions
    return render(request, 'dashboard/index.html', context)

def disconnect_ppp(request, ppp_name):
    """Desconecta una sesión PPP activa"""
    api = get_mikrotik_connection()
    if api:
        try:
            ppp_id = next((s['.id'] for s in api.path('/ppp/active').select() if s.get('name') == ppp_name), None)
            if ppp_id:
                api.path('/ppp/active').remove(ppp_id)
                messages.success(request, f'Sesión PPP {ppp_name} desconectada correctamente')
            else:
                messages.error(request, f'No se encontró la sesión PPP {ppp_name}')
        except Exception as e:
            messages.error(request, f'Error al desconectar la sesión PPP: {str(e)}')
        api.close()
    return redirect('list_ppp_sessions')

def delete_ppp(request, ppp_name):
    """Elimina un usuario PPP de MikroTik"""
    api = get_mikrotik_connection()
    if api:
        try:
            ppp_secret_id = next((s['.id'] for s in api.path('/ppp/secret').select() if s.get('name') == ppp_name), None)
            if ppp_secret_id:
                api.path('/ppp/secret').remove(ppp_secret_id)
                messages.success(request, f'Usuario PPP {ppp_name} eliminado correctamente')
            else:
                messages.error(request, f'No se encontró el usuario PPP {ppp_name}')
        except Exception as e:
            messages.error(request, f'Error al eliminar el usuario PPP: {str(e)}')
        api.close()
    return redirect('list_ppp_sessions')


def get_mikrotik_connection():
    try:
        api = connect(
            host=settings.MIKROTIK_CONFIG['host'],
            username=settings.MIKROTIK_CONFIG['username'],
            password=settings.MIKROTIK_CONFIG['password'],
            port=settings.MIKROTIK_CONFIG['port']
        )
        return api
    except Exception as e:
        return None

def disconnect_user(api, username):
    """Desconecta un usuario del hotspot"""
    try:
        # Buscar el usuario activo
        active_users = list(api.path('/ip/hotspot/active').select())
        for user in active_users:
            if user.get('user') == username:
                # Desconectar el usuario
                api.path('/ip/hotspot/active').remove(user.get('.id'))
                return True
        return False
    except Exception as e:
        return False

def index(request):
    context = {}
    api = get_mikrotik_connection()
    using_dummy_data = False
    # 🔹 Asegura que `queues` está inicializado
    queues = []
    
    if api:
        try:
            # Obtener usuarios de hotspot
            hotspot_users = list(api.path('/ip/hotspot/user').select())
            # Convertir los nombres de las claves
            for user in hotspot_users:
                if 'limit-uptime' in user:
                    user['limit_uptime'] = user.pop('limit-uptime')
            
            # Obtener interfaces
            interfaces = list(api.path('/interface').select())

            #Obtener Queues
            queues = list(api.path('/queue/simple/').select())
            for queue in queues:
                if 'max-limit' in queue:
                    queue['max_limit'] = queue.pop('max-limit')  # 🔄 Renombramos la clave
            # Obtener enlaces activos
            active_links = list(api.path('/ip/hotspot/active').select())
            # Convertir los nombres de las claves
            for link in active_links:
                if 'mac-address' in link:
                    link['mac_address'] = link.pop('mac-address')
            
            # Verificar estado de pagos
            for link in active_links:
                try:
                    payment = UserPayment.objects.get(username=link['user'])
                    link['payment_status'] = payment.check_payment_status()
                    link['next_payment'] = payment.next_payment_date
                    link['auto_disconnect'] = payment.auto_disconnect
                    
                    # Desconectar si está vencido y auto_disconnect está activado
                    if not link['payment_status'] and payment.auto_disconnect:
                        disconnect_user(api, link['user'])
                except UserPayment.DoesNotExist:
                    link['payment_status'] = True
                    link['next_payment'] = None
                    link['auto_disconnect'] = False
            
            context.update({
                'hotspot_users': hotspot_users,
                'interfaces': interfaces,
                'queues': queues,
                'active_links': active_links,
            })
            
            api.close()
        except Exception as e:
            context['error'] = str(e)
            using_dummy_data = True
    else:
        using_dummy_data = True
    
    if using_dummy_data:
        hotspot_users, interfaces, active_links = get_dummy_data()
        # Agregar datos dummy de pagos
        for link in active_links:
            link['payment_status'] = random.choice([True, False])
            link['next_payment'] = (datetime.now() + timedelta(days=random.randint(-10, 30))).date()
            link['auto_disconnect'] = random.choice([True, False])
        
        context.update({
            'hotspot_users': hotspot_users,
            'interfaces': interfaces,
            'active_links': active_links,
            'queues': queues,
            'warning': '⚠️ Se están utilizando datos de prueba. No se pudo conectar al Mikrotik.'
        })
    
    return render(request, 'dashboard/index.html', context)

def disconnect_user_view(request, username):
    api = get_mikrotik_connection()
    if api:
        if disconnect_user(api, username):
            messages.success(request, f'Usuario {username} desconectado exitosamente')
        else:
            messages.error(request, f'No se pudo desconectar al usuario {username}')
        api.close()
    else:
        # Cuando no hay conexión, solo actualizamos el estado en la base de datos
        try:
            payment = UserPayment.objects.get(username=username)
            payment.is_active = not payment.is_active
            payment.save()
            status = "desconectado" if not payment.is_active else "conectado"
            messages.info(request, f'Estado del usuario {username} actualizado a {status} (sin conexión al Mikrotik)')
        except UserPayment.DoesNotExist:
            messages.error(request, f'No se encontró el usuario {username}')
    return redirect('index')

def toggle_auto_disconnect(request, username):
    try:
        payment = UserPayment.objects.get(username=username)
        payment.auto_disconnect = not payment.auto_disconnect
        payment.save()
        messages.success(request, f'Desconexión automática {"activada" if payment.auto_disconnect else "desactivada"} para {username}')
    except UserPayment.DoesNotExist:
        messages.error(request, f'No se encontró el usuario {username}')
    return redirect('index')
