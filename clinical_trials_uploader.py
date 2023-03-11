import datetime
import json
import os
import shutil
from zipfile import ZipFile

import pymongo
import wget


def create_directory(path_to_dir, name):
    mypath = f'{path_to_dir}/{name}'
    if not os.path.isdir(mypath):
        os.makedirs(mypath)


def delete_directory(path_to_directory):
    if os.path.exists(path_to_directory):
        shutil.rmtree(path_to_directory)
    else:
        print("Directory does not exist")


def get_collection_from_db(data_base, collection, client):
    db = client[data_base]
    return db[collection]


def download_file(url, file_name):
    try:
        wget.download(url, file_name)
    except:
        download_file(url, file_name)


def upload_clinical_trials():
    clinical_trials_collection = get_collection_from_db('db', 'clinical_trials', client)
    organizations_collection = get_collection_from_db('db', 'clinical_trials_organizations', client)
    update_collection = get_collection_from_db('db', 'update_collection', client)
    current_directory = os.getcwd()
    directory_name = 'clinical_trials'
    path_to_directory = f'{current_directory}/{directory_name}'
    delete_directory(path_to_directory)
    create_directory(current_directory, directory_name)
    path_to_zip = f'{path_to_directory}/AllAPIJSON.zip'
    download_file('https://ClinicalTrials.gov/AllAPIJSON.zip', path_to_zip)
    total_trials = clinical_trials_collection.estimated_document_count()
    # existed_nct = [x.get('nct_id') for x in clinical_trials_collection.find({}, {'nct_id': 1, '_id': 0})]
    with ZipFile(path_to_zip, 'r') as zip:
        zip_files = zip.namelist()
        zip_files.remove('Contents.txt')
        l_z = len(zip_files)
        # zip_files = [file for file in zip_files if file[-16:-5] not in existed_nct]
        for index, file in enumerate(zip_files):
            print(f'{index} of {l_z}')
            if not clinical_trials_collection.find_one({'nct_id': file[-16:-5]}):
                zip.extract(file, path=path_to_directory, pwd=None)
                with open(f'{path_to_directory}/{file}', 'r', encoding='utf-8') as json_file:
                    data = json.load(json_file)
                    organization = data.get('FullStudy').get('Study').get('ProtocolSection').get(
                        'IdentificationModule').get('Organization').get('OrgFullName')
                    nct_id = data.get('FullStudy').get('Study').get('ProtocolSection').get('IdentificationModule').get(
                        'NCTId')
                    upload_at = datetime.datetime.now()
                    try:
                        clinical_trials_collection.insert_one(
                            {'organization': organization, 'nct_id': nct_id, 'upload_at': upload_at, 'data': data})
                    except pymongo.errors.DuplicateKeyError:
                        continue
    delete_directory(path_to_directory)

    last_len_trials_records = clinical_trials_collection.estimated_document_count()
    update_query = {'name': 'clinical_trials', 'new_records': total_trials - last_len_trials_records,
                    'total_records': total_trials,
                    'update_date': datetime.datetime.now()}
    if update_collection.find_one({'name': 'clinical_trials'}):
        update_collection.update_one({'name': 'clinical_trials'}, {"$set": update_query})
    else:
        update_collection.insert_one(update_query)

    organizations = list(
        set([i.get('organization') for i in list(clinical_trials_collection.find({}, {'_id': 0, 'organization': 1}))]))
    last_len_records = len(organizations)
    for organization in list(organizations):
        list_organization_trials = [trial.get('nct_id') for trial in list(clinical_trials_collection.find(
            {'organization': organization}, {'_id': 0, 'nct_id': 1}))]
        if organizations_collection.find_one({'name': organization}) is None:
            organizations_collection.insert_one({'organization': organization, 'nct_ids': list_organization_trials})
        else:
            organizations_collection.update_one({'organization': organization},
                                                {'$set': {'nct_ids': list_organization_trials}})

    total_records = organizations_collection.estimated_document_count()
    update_query = {'name': 'clinical_trials_organizations', 'new_records': total_records - last_len_records,
                    'total_records': total_records,
                    'update_date': datetime.datetime.now()}
    if update_collection.find_one({'name': 'clinical_trials'}):
        update_collection.update_one({'name': 'clinical_trials'}, {"$set": update_query})
    else:
        update_collection.insert_one(update_query)


if __name__ == '__main__':
    while True:
        client = pymongo.MongoClient('mongodb://localhost:27017')
        upload_clinical_trials()
        client.close()
