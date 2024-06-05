from redis_om import Field, JsonModel
from redis_om.model import NotFoundError
from typing import Optional


class ProcessModel(JsonModel):
    class Meta:
        global_key_prefix = 'h'
        model_key_prefix = 'ProcessModel'
    pmid: int = Field(index=True)
    creator: str = Field(index=True) #userid in UserRole
    create_time: int = Field(index=True) # the time process model is created
    group: str = Field(index=True) #the permitted groups for the ShareFlow public_id
    pm_name: str = Field(index=True)#process model name
    pm_content: str = Field(index=True)# process model content


def fetch_process_model_by_name(name):
    query = ProcessModel.find(ProcessModel.pm_name == name)
    total = query.all()
    return total[0] if len(total) > 0 else None


def get_process_model(pk):
    process_model = ProcessModel.get(pk)
    process_model_dict = process_model.dict()
    return process_model_dict


def create_process_model(
        pmid,
        creator,
        create_time,
        group,
        pm_name,
        pm_content,):
    pm = fetch_process_model_by_name(pm_name)
    if pm:
        print("none >>> ")
        return None
    process_model = ProcessModel(
        pmid = pmid,
        creator = creator,
        create_time = create_time,
        group = group,
        pm_name = pm_name,
        pm_content = pm_content,
    )
    process_model.save()
    return process_model


def update_process_model(name, update):
    process_model = fetch_process_model_by_name(name)
    if process_model:
        # process_model.creator = update.get('creator')
        # process_model.group = update.get('group')
        # process_model.pm_name = update.get('pm_name')
        process_model.pm_content = update.get('pm_content')

        process_model.save()
        return process_model
    else:
        return None


def delete_process_model(pk):
    try:
        ProcessModel.delete(pk)
    except:
        return False
    else:
        return True
