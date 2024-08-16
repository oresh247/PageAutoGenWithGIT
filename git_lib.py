import os
import sys
from git import Repo
import re

def get_repo(repo_url, clone_path):
    """Получает репозиторий из указанного URL или открывает существующий."""
    if os.path.exists(clone_path):
        try:
            print(f"Использование существующего каталога: {clone_path}...")
            repo = Repo(clone_path)
            return repo
        except Exception as e:
            print(f"Ошибка при открытии существующего репозитория: {e}")
            sys.exit(1)
    else:
        # Клонирование репозитория
        try:
            print(f"Клонирование репозитория из {repo_url} в {clone_path}...")
            #repo = Repo.clone_from(repo_url, clone_path, branch='develop', single_branch=True)
            repo = Repo.clone_from(repo_url, clone_path, branch='develop')
            #repo = Repo.clone_from(repo_url, clone_path)
            return repo
        except Exception as e:
            print(f"Ошибка при клонировании репозитория: {e}")
            sys.exit(1)


def get_branches_with_tag(repo, tag):
    """
    Получает список веток, в которые залит коммит с указанным тегом.

    Args:
        repo (Repo): Объект репозитория Git.
        tag (str): Тег, для которого нужно найти ветки.

    Returns:
        list: Список названий веток, содержащих коммит с тегом.
    """
    branches = []

    # Попытка получить объект тега
    try:
        tag_obj = repo.tags[tag]
    except IndexError:
        print(f"Ошибка: Тег '{tag}' не найден в репозитории.")
        return branches  # Возвращаем пустой список, если тег не найден

    # Получаем хэш коммита, связанного с тегом
    commit_hash = tag_obj.commit.hexsha

    # Итерируем по всем веткам
    for branch in repo.branches:
        # Проверяем, содержит ли ветка коммит с тегом
        if repo.git.branch('--contains', commit_hash, branch.name):
            branches.append(branch.name)

    return branches


def update_repo(repo):
    """Обновляет локальный репозиторий из удаленного."""
    try:
        # Получение изменений из удаленного репозитория
        print("Получение изменений из удаленного репозитория...")
        repo.remotes.origin.fetch()

        # Обновление текущей ветки
        print("Обновление текущей ветки...")
        repo.git.pull()
        print("Репозиторий успешно обновлен.")
    except Exception as e:
        print(f"Ошибка при обновлении репозитория: {e}")
    return repo


def switch_to_branch(repo, branch_name):
    """Переключается на указанную ветку."""
    if 'origin/' in branch_name:
        branch_name = branch_name.replace('origin/','')
    # Проверяем, существует ли ветка в локальных ветках
    if branch_name in repo.branches:
        branch = repo.heads[branch_name]
        repo.git.checkout(branch)
        print(f"\nПереключено на локальную ветку '{branch_name}'.")
        print(f"Активная ветка '{repo.active_branch.name}'")
        return True

    # Проверяем, существует ли ветка в удаленных репозиториях
    remote_branch_name = f'origin/{branch_name}'  # Формируем имя удаленной ветки
    print(repo.remotes.origin.refs)
    if any(ref.name == remote_branch_name for ref in repo.remotes.origin.refs):
        # Создаем локальную ветку на основе удаленной и переключаемся на нее
        repo.git.checkout('-b', branch_name, remote_branch_name)
        print(f"Переключено на удаленную ветку '{remote_branch_name}' и создана локальная ветка '{branch_name}'.")
        print(f"Активная ветка '{repo.active_branch.name}'")
        return True

    print(f"Ветка '{branch_name}' не найдена.")
    return False


def get_file_from_repo(repo, file_name):
    """Возвращает содержимое указанного файла из репозитория."""
    try:
        # Получаем текущую ветку
        current_branch = repo.active_branch.name

        # Получаем объект файла в текущей ветке
        file_path = os.path.join(repo.working_tree_dir, file_name)

        # Проверяем, существует ли файл
        if os.path.isfile(file_path):
            with open(file_path, 'r') as file:
                content = file.read()
            return content
        else:
            return f"Файл '{file_name}' не найден в ветке '{current_branch}'."

    except Exception as e:
        return f"Ошибка при получении файла: {e}"


def get_version(text1, text2, lib_name):
    pattern1 = r'\S*\s*' + lib_name + '\s*:\s*(\S+)'
    match1 = re.search(pattern1, text1)
    if match1:
        result = match1.group(1)
        if '$' in result:
            pattern2 = r'\$\{(\S+)\}'
            match2 = re.search(pattern2, result)
            if match2:
                result = match2.group(1)   # Возвращаем значение внутри фигурных скобок
                pattern3 = result + r'\s*=\s*(\S+)'
                match3 = re.search(pattern3, text2)
                if match3:
                    result = match3.group(1)

        result = result.replace('"', '')
        result = result.replace("'", '')

        return result  # Возвращаем версию из implementation
    return ''  # Если ни одна версия не найдена