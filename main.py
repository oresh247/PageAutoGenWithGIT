# coding:utf-8
import configparser
import html
import json
import re
import warnings

import numpy as np
import pandas as pd
import requests
import git_lib as glib


warnings.filterwarnings("ignore")

config = configparser.ConfigParser()
configJira = configparser.ConfigParser()
config.read("config.ini", encoding='utf-8')
configJira.read("configFields.ini", encoding='utf-8')


# СФЕРА параметры
devUser = config["SFERAUSER"]["devUser"]
devPassword = config["SFERAUSER"]["devPassword"]
sferaUrl = config["SFERA"]["sferaUrl"]
sferaUrlLogin = config["SFERA"]["sferaUrlLogin"]
sferaTestCaseUrl = config["SFERA"]["sferaTestCaseUrl"]
sferaTSectionsUrl = config["SFERA"]["sferaTSectionsUrl"]
sferaSprintUrl = config["SFERA"]["sferaSprintUrl"]
sferaUrlSearch = config["SFERA"]["sferaUrlSearch"]
sferaUrlKnowledge = config["SFERA"]["sferaUrlKnowledge"]
sferaUrlKnowledge2 = config["SFERA"]["sferaUrlKnowledge2"]
sferaUrlRelations = config["SFERA"]["sferaUrlRelations"]
sferaUrlEntityViews = config["SFERA"]["sferaUrlEntityViews"]
sferaUrlSkmbRepos = config["SFERA"]["sferaUrlSkmbRepos"]
sferaUrlDelete = config["SFERA"]["sferaUrlDelete"]
sferaUrlSkmbTestiPlan = config["SFERA"]["sferaUrlSkmbTestiPlan"]
sferaUrlTestiPlan = config["SFERA"]["sferaUrlTestiPlan"]
sferaUrlSkmbTestiIssues = config["SFERA"]["sferaUrlSkmbTestiIssues"]

GIT_LINK = config["GIT"]["GIT_LINK"]
GIT_PATH = config["GIT"]["GIT_PATH"]
GIT_BRANCH_PREFIX = config["GIT"]["GIT_BRANCH_PREFIX"]

TASK_RELATION_TYPE_LST = json.loads(config["TASK"]["TASK_RELATION_TYPE_LST"])
TASK_ENTITY_TYPE_LST = json.loads(config["TASK"]["TASK_ENTITY_TYPE_LST"])
SERVICE_VTBL_NOTIFICATION_LST = json.loads(config["TASK"]["SERVICE_VTBL_NOTIFICATION_LST"])

session = requests.Session()
session.post(sferaUrlLogin, json={"username": devUser, "password": devPassword}, verify=False)


def get_release_tasks(release):
    """
    Функция возвращает список задач релиза в виде массива json
    :param release: str
         Номер релиза
    :return json.loads(response.text): str
        Текст ответа на запрос в формате json
    """
    # Формируем запрос
    query = 'label%20%3D%20%27' + release + '%27&size=1000&page=0&attributesToReturn=checkbox%2Cnumber%2Cname%2CactualSprint%2Cpriority%2Cstatus%2Cassignee%2Cowner%2CdueDate%2Clabel%2CparentNumber%2Ccomponent'
    url = sferaUrlSearch + "?query=" + query
    # Делаем запрос задач по фильтру
    response = session.get(url, verify=False)
    if response.ok != True:
        raise Exception("Error get sprint data " + response)
    return json.loads(response.text)


def get_task_comments(task_number):
    """
    Функция возвращает массив комментариев к задаче в виде json массива
    :param task_number: str
        Номер задачи
    :return: str
        Текст ответа на запрос в формате json
    """
    # Формируем запрос
    path = '/attributes/comments?'
    query = 'sort=createDate,desc&size=1000'
    url = sferaUrlEntityViews + task_number + path + query
    # Делаем запрос задач по фильтру
    response = session.get(url, verify=False)
    if response.ok != True:
        raise Exception("Error get sprint data " + response)
    return json.loads(response.text)


def generate_release_html(tasks_df):
    # Генерируем HTML-код
    html_code = tasks_df.to_html(index=False)

    # Декодируем HTML-спецсимволы
    decoded_html = html.unescape(html_code)
    decoded_html = str.replace(decoded_html, '\n', '')
    decoded_html = str.replace(decoded_html, '\\n', '')
    decoded_html = str.replace(decoded_html, '"', '')
    decoded_html = str.replace(decoded_html, "'", '"')
    decoded_html = str.replace(decoded_html, 'class=sfera-link sfera-task sfera-link-style',
                               'class="sfera-link sfera-task sfera-link-style"')
    decoded_html = str.replace(decoded_html, '<table border=1 class=dataframe>',
                               '<table class="MsoNormalTable" border="1" cellspacing="0" cellpadding="0" width="1440" data-widthmode="wide" data-lastwidth="1761px" style="border-collapse: collapse; width: 1761px;" data-rtc-uid="67d29bf0-31c7-4de5-909d-8cea7a11f75f" id="mce_2">')
    return decoded_html


def publication_release_html(html, parentPage, page_name):
    data = {
        "spaceId": "cbbcfa0b-0542-4407-9e49-61c6aa7caf1b",
        "parentCid": parentPage,
        "name": page_name,
        "content": html
    }
    response = session.post(sferaUrlKnowledge2, json=data, verify=False)
    if response.ok != True:
        raise Exception("Error creating story " + response)
    return json.loads(response.text)


def replace_release_html(html, parentPage, page_name, page_id):
    url1 = sferaUrlKnowledge + 'cid/' + page_id
    response = session.get(url1, verify=False)
    id = json.loads(response.text)['payload']['id']
    data = {
        "id": id,
        "content": html,
        "name": page_name
    }
    url2 =sferaUrlKnowledge2 + '/' + page_id
    response = session.patch(url2, json=data, verify=False)
    if response.ok != True:
        raise Exception("Error creating story " + response)
    return json.loads(response.text)


def get_prod_versions(file_path):
    prod = pd.read_csv(file_path, header=None, names=['data'])

    def get_service(value):
        lst = str.split(value, ' ')
        return lst[0]

    def get_version(value):
        lst = str.split(value, ' ')
        return lst[-1]

    prod['service'] = prod['data'].map(get_service)
    prod['version'] = prod['data'].map(get_version)
    prod.drop(columns=['data'], inplace=True)
    return prod


def get_file_edto_name(file_path):
    file_names = pd.read_csv(file_path, header=None, names=['data'])

    def get_service(value):
        lst = str.split(value, ' ')
        return lst[0]

    def get_file_names(value):
        lst = str.split(value, ' ')
        return lst[-1]

    file_names['service'] = file_names['data'].map(get_service)
    file_names['file_name'] = file_names['data'].map(get_file_names)
    file_names.drop(columns=['data'], inplace=True)
    return file_names


def get_edto_version_from_git(component_name, new_version):
    skmb_reactive_dto = ''
    clone_path = GIT_PATH + component_name
    repo_url = GIT_LINK + component_name + '.git'

    try:
        repo = glib.get_repo(repo_url, clone_path)
    except SystemExit:
        return skmb_reactive_dto

    repo = glib.update_repo(repo)
    branches = glib.get_branches_with_tag(repo, new_version)
    if branches:
        glib.switch_to_branch(repo, branches[0])
        repo = glib.update_repo(repo)
        file_content1 = glib.get_file_from_repo(repo, 'build.gradle')
        file_content2 = glib.get_file_from_repo(repo, 'gradle.properties')
        skmb_reactive_dto = glib.get_version(file_content1, file_content2, 'skmb-reactive-dto')
        print(f"верксия бтблиотеки skmb_reactive_dto:'{skmb_reactive_dto}'")
    return skmb_reactive_dto


def formation_of_lists(tasks, release, prod, edto_file_names, new_version):
    component_lst = [] # Список микросервисов релиза
    task_directLink_lst = [] # Список строк HTML для добавления макроса в таблицу по каждому микросервису
    prod_version_lst = []  # Список версий ПРОДа по каждому микросервису
    task_lst = [] # Список номеров задач релиза по каждому микросервису
    inventory_changed_lst = [] # Список изменений инвентари по каждому микросервису
    inventory_changed_dic = {}
    edto_lst = [] # Список версий еДТО по каждому микросервису
    edto_dic = {}
    task_comments_dic = {}
    task_comments_lst = []  # Список версий еДТО по каждому микросервису
    related_task_dic = {}
    tast_cases_dic = {}
    service_release_version_dic = {}
    service_edto_version_dic = {}

    counter = 10 # Начальный счетчик макросов на странице
    #test_cases = get_release_test_cases(release)

    # Перебираем массив задач релиза
    for task in tasks['content']:
        new_task = task['number']
        component_name = ''
        inventory = ''
        service_build = '' # Предварительно обнуляем номер сборки для задачи


        if new_task not in task_lst:
            task_lst.append(new_task)

        if 'component' in task:
            for component in task['component']:
                component_name = component['name']
                if component_name not in component_lst:
                    component_lst.append(component['name'])
                    inventory_changed_dic[component_name] = ''
                    task_comments_dic[component_name] = ''
                    #edto_dic[component_name] = get_edto_version_from_git(component_name, new_version)
                    #edto_dic[component_name] = get_edto_version(component_name, new_version, edto_file_names)
                    template = f"""
            <p>  <macro class=is-locked data-name=SferaTasks id=SferaTasks-mce_{counter} contenteditable=false    data-rtc-uid=16cce9cf-5572-4a48-a85b-3375c3c8ed6d><macro-parameter data-name=query      data-rtc-uid=d2a03405-badc-4db9-b558-c63defb0c191>label = '{release}' and      component='{component_name}'</macro-parameter><macro-parameter data-name=name      data-rtc-uid=299855c1-a21a-4a91-88b3-99539008e3c6>{release}_{component_name}</macro-parameter><macro-parameter      data-name=maxTasks data-rtc-uid=4a9ba1c3-6e18-4939-a108-7890b7347054>20</macro-parameter><macro-parameter      data-name=attributes      data-rtc-uid=150ff77e-2639-48fa-bba0-32dd06b4104f>[{{'name':'Ключ','code':'number'}},{{'name':'Название','code':'name'}},{{'name':'Статус','code':'status'}},{{'name':'Исполнитель','code':'assignee'}}]</macro-parameter><macro-parameter      data-name=createdDate      data-rtc-uid=05fa3e33-7799-4ddc-bc7e-316a518aeeaa>1716579558662</macro-parameter><macro-parameter      data-name=isLocked      data-rtc-uid=3ba10cb8-4865-45c1-aae9-0e8c5437f9c8>false</macro-parameter><macro-rich-text      data-rtc-uid=5dfe052c-765d-4974-8d5d-4d3e356f9bd9></macro-rich-text></macro></p>
            """
                    counter += 1
                    task_directLink_lst.append(template)
                    matching_rows = prod[prod['service'].str.contains(component_name)]
                    if not matching_rows.empty:
                        version = matching_rows['version'].values[0]
                        prod_version_lst.append(version)
                    else:
                        prod_version_lst.append('')
                    # Есть сервисы ВТБЛ и требуется добавление информации в комментарий об оповещении
                    if component_name in SERVICE_VTBL_NOTIFICATION_LST:
                        task_comments_dic[component_name] = "ТРЕБУЕТ ОПОВЕЩЕНИЯ ВТБЛ О РЕЛИЗЕ!"

        else:
            print("Нет компоненты: ",task['number'])


        # Учитываем дополнительные параметры задачи, если указан микросервис
        if component_name != '':
            # Обрабатываем комментарий
            comments = get_task_comments(new_task)

            # Получаем прописанные инвентари в комментариях задачи
            inventory = get_comment_text(comments, '#inventory', 0)
            # Если есть изменения инвентори
            if inventory != '':
                if inventory_changed_dic[component_name] != '':
                    inventory_changed_dic[component_name] = inventory_changed_dic[component_name] + '\n' + inventory
                else:
                    inventory_changed_dic[component_name] ='Изменение инвентори:\n' + inventory

            # Получаем последнюю сборку прописанную в комментариях задачи
            service_build = get_comment_text(comments, '#build', 1)
            # # Если есть номер сборки
            # if service_build != '':
            #     # Получаем сборку еДТО
            #     service_edto_version = get_edto_version(component_name, service_build, edto_file_names)
            #     #service_edto_version = get_edto_version_from_git(component_name, service_build)
            #     if service_edto_version != '':
            #         if component_name in inventory_changed_dic:
            #             edto_dic[component_name] = edto_dic[component_name] + '<br>' + service_edto_version
            #         else:
            #             edto_dic[component_name] = service_edto_version

            # Получаем комментарии к задаче
            task_comments = get_comment_text(comments, '#comment', 0)
            # Если есть комментарии к задаче
            if task_comments != '':
                if task_comments_dic[component_name] != '':
                    task_comments_dic[component_name] =task_comments_dic[component_name] + '<br>' + '<br>' + f'{new_task}:' + task_comments
                else:
                    task_comments_dic[component_name] =f'{new_task}:' + task_comments

            # Получаем версию поставки прописанную в комментариях задачи
            task_comments = get_comment_text(comments, '#version', 0)
            if component_name not in service_release_version_dic:
                service_release_version_dic[component_name] = task_comments

            # Получаем версию еДТО прописанную в комментариях задачи
            task_comments = get_comment_text(comments, '#edto', 0)
            if component_name not in service_edto_version_dic:
                service_edto_version_dic[component_name] = task_comments


            # Обрабатываем связанные задачи
            current_task = getSferaTask(new_task)
            related_components = ''
            if 'relatedEntities' in current_task:
                for related_entity in current_task['relatedEntities']:
                    if related_entity['relationType'] in TASK_RELATION_TYPE_LST:
                        if related_entity['entity']['type'] in TASK_ENTITY_TYPE_LST:
                            related_task_id = related_entity['entity']['number']
                            related_task = getSferaTask(related_task_id)
                            related_component_name = ''
                            if 'component' in related_task:
                                for component in related_task['component']:
                                    related_component_name = component['name']

                            related_components = related_components + '<br>' + f"{new_task} - {related_task_id} [{related_component_name}]"

            # Если есть связанные задачи
            if component_name in related_task_dic:
                related_task_dic[component_name] = related_task_dic[component_name] + related_components
            else:
                related_task_dic[component_name] = related_components

            # Ищем тест-кейсы по номеру задачи
            test_case = get_test_case_by_task_name(new_task)
            # Если есть тест-кейсы
            if component_name in tast_cases_dic:
                tast_cases_dic[component_name] = tast_cases_dic[component_name] + '<br>' + test_case
            else:
                tast_cases_dic[component_name] = test_case



    return component_lst, task_directLink_lst, prod_version_lst, task_lst, list(inventory_changed_dic.values()), list(edto_dic.values()), list(task_comments_dic.values()), list(related_task_dic.values()), list(tast_cases_dic.values()), list(service_release_version_dic.values()), list(service_edto_version_dic.values())


def get_comment_text(comments, tag, template_flag):
    text = ''
    if 'content' in comments:
        for comment in comments['content']:
            comment_text = comment['text']
            if tag in comment_text:
                if template_flag == 0:
                    text = text + '<br>' + comment_text
                    text = text.replace(tag, '')
                    text = text.replace('\n', '<br>')
                if template_flag == 1 and text == '':
                    text = str.split(comment_text)[-1]
    return text


def find_dto_version(text):
    # Используем регулярное выражение для поиска строки с dto_exchange_version
    pattern_dto_version = r'reactive_dto_version\s*=\s*(\S+)'
    match_dto_version = re.search(pattern_dto_version, text)

    if match_dto_version:
        return match_dto_version.group(1)  # Возвращаем версию из dto_exchange_version

    # Новый паттерн для поиска версии из подстроки skmb-reactive-dto
    pattern_implementation = r'\S*\s*skmb-reactive-dto\s*:\s*(\S+)'
    match_implementation = re.search(pattern_implementation, text)

    if match_implementation:
        return match_implementation.group(1)  # Возвращаем версию из implementation

    return ''  # Если ни одна версия не найдена


def get_edto_version(component_name, service_build, edto_file_names):
    path = '/file/raw/'
    #file_name = 'gradle.properties'

    matching_rows = edto_file_names[edto_file_names['service'].str.contains(component_name)]
    if not matching_rows.empty:
        file_name = matching_rows['file_name'].values[0]
    else:
        file_name = 'gradle.properties'

    query = '?rev=' + service_build
    url = sferaUrlSkmbRepos + component_name + path + file_name + query
    # Делаем запрос задач по фильтру
    response = session.get(url, verify=False)
    if response.ok != True:
        #raise Exception("Error get sprint data " + response)
        return ''
    return find_dto_version(response.text)


def create_df(component_lst, task_directLink_lst, prod_version_lst, new_version, inventory_changed_lst, edto_lst, task_comments_lst, related_task_lst, tast_cases_lst, service_release_version_lst, service_edto_version_lst):
    # Проверка на пустоту списка inventory_changed_lst
    if not inventory_changed_lst:
        inventory_changed_lst = [''] * len(component_lst)  # Заполнение пустыми строками, если список пустой
    # Проверка на пустоту списка edto_lst
    # if not edto_lst:
    #     edto_lst = [''] * len(component_lst)  # Заполнение пустыми строками, если список пустой
    # Проверка на пустоту списка task_comments_lst
    if not task_comments_lst:
        task_comments_lst = [''] * len(component_lst)  # Заполнение пустыми строками, если список пустой
    # Проверка на пустоту списка related_task_lst
    if not related_task_lst:
        related_task_lst = [''] * len(component_lst)  # Заполнение пустыми строками, если список пустой
    # Проверка на пустоту списка tast_cases_lst
    if not tast_cases_lst:
        tast_cases_lst = [''] * len(component_lst)  # Заполнение пустыми строками, если список пустой
    # Проверка на пустоту списка service_release_version_lst
    if not service_release_version_lst:
        service_release_version_lst = [new_version] * len(component_lst)  # Заполнение номером версии поставки Новый цод строками
    # Проверка на пустоту списка service_edto_version_lst
    if not service_edto_version_lst:
        service_edto_version_lst = [new_version] * len(
            component_lst)  # Заполнение номером версии поставки Новый цод строками


    # Заменить пустые значения на строку 'нет зависимостей'
    related_task_lst = ['нет зависимостей' if item == '' else item for item in related_task_lst]

    # Заменить пустые значения на строку 'нет зависимостей'
    service_edto_version_lst = ['не обновляли еДТО' if item == '' else item for item in service_edto_version_lst]

    # Заменить пустые значения версий на new_version
    service_release_version_lst = [new_version if item == '' else item for item in service_release_version_lst]

    tasks_df = pd.DataFrame({
        'Сервис': component_lst,
        'Задачи в сфере': task_directLink_lst,
        'Версия поставки Новый цод': service_release_version_lst,
        'Версия для откатки': prod_version_lst,
        'Требует выкатку связанный сервис': related_task_lst,
        'Версия еДТО': service_edto_version_lst,
        'Тест-кейсы': tast_cases_lst,
        'Изменение инвентари': inventory_changed_lst,
        'Комментарии': task_comments_lst
    })
    # Сортировка DataFrame по столбцу 'component_lst'
    tasks_df = tasks_df.sort_values(by='Сервис')
    return tasks_df


def generating_release_page(parent_page, release, new_version, for_publication_flg, replace_flg, page_id):
    # Загружаем версии ПРОДа
    prod = get_prod_versions('data/prod.csv')

    # Загружаем имена файлов
    edto_file_names = get_file_edto_name('data/file_for_edto.csv')

    # загружаем задачи релиза
    tasks = get_release_tasks(release)

    # Обрабатываем запрос, проходя по всем задачам и формируя списки
    component_lst, task_directLink_lst, prod_version_lst, task_lst, inventory_changed_lst, edto_lst, task_comments_lst, related_task_lst, tast_cases_lst, service_release_version_lst, service_edto_version_lst = formation_of_lists(tasks, release, prod, edto_file_names, new_version)

    # Создаем dataframe
    tasks_df = create_df(component_lst, task_directLink_lst, prod_version_lst, new_version, inventory_changed_lst, edto_lst, task_comments_lst, related_task_lst, tast_cases_lst, service_release_version_lst, service_edto_version_lst)
    pd.set_option('display.width', 320)
    pd.set_option('display.max_columns', 20)
    np.set_printoptions(linewidth=320)
    print(tasks_df)

    # Формируем HTML таблицу
    html = generate_release_html(tasks_df)

    # Публикуем страницу
    if for_publication_flg:
        if replace_flg:
            replace_release_html(html, parent_page, release, page_id)
        else:
            publication_release_html(html, parent_page, release)
    return task_lst


def add_task_to_story(task_list,story):
    for task in task_list:
        data = {
        "entityNumber": story,
        "relatedEntityNumber": task,
        "relationType": "associatedbugsandstories"
        }
        response = session.post(sferaUrlRelations, json=data, verify=False)
        # if response.ok != True:
        #     raise Exception("Error creating story " + response)


def createSferaTask(release):
    data = {
        "name": "Релиз " + release,
        "assignee": devUser,
        "owner": devUser,
        "estimation": 28800,
        "remainder": 28800,
        "description": "Релиз " + release,
        "priority": "average",
        "status": "created",
        "type": "story",
        "areaCode": "SKOKR",
        "customFieldsValues": [
            {
                "code": "streamConsumer",
                "value": "Скоринговый конвейер КМБ"
            },
            {
                "code": "streamOwner",
                "value": "Скоринговый конвейер КМБ"
            },
            {
                "code": "projectConsumer",
                "value": "da2bc81b-5928-4f05-a7f4-4a9a5e48ce68"
            },
            {
                "code": "workGroup",
                "value": "Новая функциональность"
            },
            {
                "code": "systems",
                "value": "1864 Скоринговый конвейер кредитования малого бизнеса"
            },
            {
                "code": "changeType",
                "value": "Создание/Доработка ИС"
            },
            {
                "code": "decision",
                "value": "! Нет решения"
            },
            {
                "code": "rightTransferApproval",
                "value": 'true'
            },
            {
                "code": "acceptanceCriteria",
                "value": "Функциональность успешно выведена в ПРОД"
            },
            {
                "code": "artifactsCreateRework",
                "value": "Архитектура ИС"
            },
            {
                "code": "artifactsCreateRework",
                "value": "ПМИ ИС"
            },
            {
                "code": "artifactsCreateRework",
                "value": "Протокол тестирования ИС"
            },
            {
                "code": "artifactsCreateRework",
                "value": "Тестовые планы и сценарии ИС"
            },
            {
                "code": "artifactsCreateRework",
                "value": "Тестовые планы и сценарии Решения"
            },
            {
                "code": "artifactsCreateRework",
                "value": "Требования к ИС"
            },
            {
                "code": "lackLoadTestReason",
                "value": "Решение лидера команды развития"
            },
            {
                "code": "isContractorWork",
                "value": "Не определено"
            }
        ]
    }

    response = session.post(sferaUrlSearch, json=data, verify=False)
    if response.ok != True:
        raise Exception("Error creating story " + response)
    return json.loads(response.text)


def get_links(taskId):
    story_data = getSferaTask(taskId)
    relation_lst = []
    for task in story_data['relatedEntities']:
        relation_lst.append(task['relationId'])
    return relation_lst


def delete_links(taskId, relation_lst):
    for relation_id in relation_lst:
        url = sferaUrlDelete + taskId + '/attributes/relations/' + str(relation_id)
        response = session.delete(url, verify=False)


def getSferaTask(taskId):
    url = sferaUrl + taskId
    response = session.get(url, verify=False)
    return json.loads(response.text)


def get_test_plans(search_string):
    query = "?sort=entityInfo.createdAt%2Cdesc&page=0&size=50&searchString="
    url = sferaUrlSkmbTestiPlan + query + search_string
    response = session.get(url, verify=False)
    if response.ok != True:
        return ""
    return json.loads(response.text)


def get_test_cases(test_plan_code):
    url = sferaUrlTestiPlan + test_plan_code + '/test-plan-cases'
    response = session.get(url, verify=False)
    if response.ok != True:
        return ''
    return json.loads(response.text)


def get_test_case_by_task_name(new_task):
    result_str = ''
    query = '?rootSectionId=137672&page=0&size=500&includeSubSections=true&sort=number%2Cdesc&searchString=' + new_task
    url = sferaUrlSkmbTestiIssues + query
    response = session.get(url, verify=False)
    if response.ok:
        test_cases = json.loads(response.text)
        if test_cases['content']:
            for test_case in test_cases['content']:
                test_case_str = new_task + ' - (' + test_case['status'] + ') ' + 'https://sfera.inno.local/testing/project/SKMB/test-issue/' + test_case['testIssueCode']
                result_str = result_str + '<br>' + test_case_str
    return result_str


def extract_date(release):
    # Split the string to get the date part
    date_part = release.split('_')[1]
    # Extract the year, month, and day
    year = date_part[:4]
    month = date_part[4:6]
    day = date_part[6:8]
    # Return the date in the desired format
    return f"{day}.{month}"


def get_test_case_by_release(test_cases, task_name):
    for test_case in test_cases:
        if task_name in test_case['name']:
            test_case_id = test_case['testCaseId']
            return test_case_id
    return ''


def get_release_test_cases(release):
    search_string = extract_date(release)
    test_plans = get_test_plans(search_string)
    if test_plans == '':
        return ''

    for test_plan in test_plans['content']:
        if 'Проверки' in test_plan['name']:
            test_plan_code = test_plan['testPlanCode']
            test_cases = get_test_cases(test_plan_code)
            return test_cases['content']
    return ''


release = 'OKR_20250316_ATM' # Метка релиза
for_publication_flg = True # Если True - то публикуем, если False, только возврат списка задач
replace_flg = True # Если True - то заменяем содержимое страницы
update_story_flg = False  # Если True - обновляем спиисок задач в story (удаляем все и добавляем те, что в текущем релизе)

# Считываем данные из CSV файла в DataFrame
release_df = pd.read_csv('release_info.csv', dtype=str)
# Извлечение данных из DataFrame по ключу (номеру релиза)
release_info = release_df[release_df['release'] == release].iloc[0]

# Задание переменных на основе данных из DataFrame
page_id = release_info['page_id']
new_version = release_info['new_version']
story = release_info['story']
parent_page = release_info['parent_page']

# Вывод переменных для проверки
print(f"page_id: {page_id}")
print(f"release: {release}")
print(f"new_version: {new_version}")
print(f"story: {story}")
print(f"parent_page: {parent_page}")

# Генерация страницы ЗНИ с QL выборками
task_lst = generating_release_page(parent_page, release, new_version, for_publication_flg, replace_flg, page_id)
if update_story_flg:
    if not isinstance(story, str):
        story = createSferaTask(release)
        add_task_to_story(task_lst, story)
        print(story)
    else:
        relation_lst = get_links(story)
        delete_links(story, relation_lst)
        add_task_to_story(task_lst, story)

