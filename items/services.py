from .models import Item
from django.core.exceptions import ObjectDoesNotExist

# NOTA: aquí ponemos la lógica del dominio (validaciones, transacciones, etc.)

def list_items():
    return list(Item.objects.all().order_by('-created_at'))

def get_item(item_id):
    try:
        return Item.objects.get(pk=item_id)
    except ObjectDoesNotExist:
        return None

def create_item(name, description=''):
    item = Item.objects.create(name=name, description=description)
    return item

def update_item(item_id, name=None, description=None):
    item = get_item(item_id)
    if not item:
        return None
    if name is not None:
        item.name = name
    if description is not None:
        item.description = description
    item.save()
    return item

def delete_item(item_id):
    item = get_item(item_id)
    if not item:
        return False
    item.delete()
    return True