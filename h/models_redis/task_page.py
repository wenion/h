from redis_om import Field, JsonModel
from redis_om.model import NotFoundError
from typing import Optional
from urllib.parse import urlparse


class TaskPage(JsonModel):
    class Meta:
        global_key_prefix = "h"
        model_key_prefix = "TaskPage"
    url: str = Field(index=True, full_text_search=True) # note: task page stores the domain of the task pages not the actual page URLs
    pm_name: str = Field(index=True)
    session_id: str = Field(index=True)


def is_task_page(url):
    parsed_url = urlparse(url)
    domain = parsed_url.netloc
    # query = TaskPage.find(TaskPage.url.__mod__(domain)) # domain must be escape characters
    query = TaskPage.find(TaskPage.url == domain)
    total = query.all()
    return True if len(total) else False


def fetch_all_task_pages():
    query = TaskPage.find()
    all_pages = query.all()
    return all_pages if len(all_pages) > 0 else None


def fetch_task_page_name_id(pm_name, session_id):
    query = TaskPage.find((TaskPage.pm_name == pm_name) & (TaskPage.session_id == session_id))
    total = query.all()
    return total if len(total) > 0 else None


def add_task_page(url, pm_name, session_id):
    page = fetch_task_page_name_id(pm_name, session_id)
    if page:
        return page
    page = TaskPage(url=url, pm_name=pm_name, session_id=session_id)
    page.save()
    return page


def delete_task_page_name_id(pm_name, session_id):
    try:
        page = fetch_task_page_name_id(pm_name, session_id)
        if page:
            for p in page:
                TaskPage.delete(p.pk)
        else:
            return False
    except:
        return False
    else:
        return True


def delete_task_page(pk):
    try:
        TaskPage.delete(pk)
    except:
        return False