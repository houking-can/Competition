import codecs
import csv
import re
from tqdm import tqdm
import pandas as pd
import random
import os

predict_dictionary = open('./data/dict/dict_oracle.txt').read().split('\n')
predict_dictionary = [each.strip() for each in predict_dictionary]
predict_dictionary = set([each for each in predict_dictionary if each != ''])

remove = set(open('./data/dict/remove.txt').read().split('\n'))
if '' in remove: remove.remove('')

none = set(open('./data/dict/dict_label_none.txt').read().split('\n'))
none = [each.strip() for each in none]
none = set([each for each in none if each != ''])
none = none - predict_dictionary

train_dict = open('./data/dict/train_dict.txt').read().split('\n')
train_dict = [each.strip() for each in train_dict]
train_dict = set([each for each in train_dict if each != ''])
train_dict = train_dict - none - predict_dictionary

bio_dictionary = list(predict_dictionary | train_dict | none)
# bio_dictionary = list(set(predict_dictionary))
bio_dictionary = sorted(bio_dictionary, key=lambda e: len(e), reverse=True)

assert ('' not in bio_dictionary)


def read_csv():
    train_df = pd.read_csv('./data/Train_Data.csv')
    train_df['text'] = train_df['title'].fillna('') + '。' + train_df['text'].fillna('')

    test_df = pd.read_csv('./data/Test_Data.csv')
    test_df['text'] = test_df['title'].fillna('') + '。' + test_df['text'].fillna('')
    return train_df, test_df


def get_sentences(text, max_length=128):
    # if len(text) <= max_length - 2:
    #     return [text]
    tmp = re.split('(。|！|？|；|，|\?|\!)', text)
    sent = ''
    sentences = []
    if tmp[-1] != '':
        tmp.append('。')
    else:
        tmp = tmp[:-1]

    i = 0
    while i < len(tmp) - 1:

        if len(sent + tmp[i] + tmp[i + 1]) > max_length - 2 and len(tmp[i]) <= 150:
            sentences.append(sent)
            sent = ''
        if tmp[i] != '' and len(tmp[i]) <= 150:
            sent += (tmp[i] + tmp[i + 1])
        i += 2
    if sent != '':
        sentences.append(sent)

    return sentences


def gen_bio():
    train_df, test_df = read_csv()
    additional_chars = set()
    for t in list(test_df.text) + list(train_df.text):
        additional_chars.update(re.findall(u'[^\u4e00-\u9fa5a-zA-Z0-9\*]', t))

    extra_chars = set("!#$%&\()*+,-./:;<=>?@[\\]^_`{|}~！#￥%&？《》{}“”，：‘’。（）·、；【】")
    additional_chars = additional_chars.difference(extra_chars)

    def remove_additional_chars(input):
        for x in additional_chars:
            input = input.replace(x, "")
        return input

    train_df["text"] = train_df["text"].apply(remove_additional_chars)
    test_df["text"] = test_df["text"].apply(remove_additional_chars)

    # gen train
    print("generate train...")
    rows = [each for each in train_df.iloc[:].itertuples()]
    with codecs.open('./data/train.txt', 'w') as up:
        for row in tqdm(rows):
            sentences = get_sentences(row.text)
            up.write('Ж{0}Ж {1}\n'.format(str(row.id), 'O'))
            for i, sent in enumerate(sentences):
                for entity in bio_dictionary:
                    sent = sent.replace(entity, 'Ё' + (len(entity) - 1) * 'Ж')
                for c1, c2 in zip(sent, sentences[i]):
                    if c1 == 'Ё':
                        up.write('{0} {1}\n'.format(c2, 'B-ORG'))
                    elif c1 == 'Ж':
                        up.write('{0} {1}\n'.format(c2, 'I-ORG'))
                    else:
                        up.write('{0} {1}\n'.format(c2, 'O'))

                up.write('\n')

    # gen dev
    print("generate dev...")
    with codecs.open('./data/dev.txt', 'w') as up:
        rows = random.sample([each for each in train_df.iloc[:].itertuples()], 100)
        for row in tqdm(rows):
            sentences = get_sentences(row.text)
            up.write('Ж{0}Ж {1}\n'.format(str(row.id), 'O'))
            for i, sent in enumerate(sentences):
                if len(sent) < 2:
                    continue
                for entity in bio_dictionary:
                    sent = sent.replace(entity, 'Ё' + (len(entity) - 1) * 'Ж')

                for c1, c2 in zip(sent, sentences[i]):
                    if c1 == 'Ё':
                        up.write('{0} {1}\n'.format(c2, 'B-ORG'))
                    elif c1 == 'Ж':
                        up.write('{0} {1}\n'.format(c2, 'I-ORG'))
                    else:
                        up.write('{0} {1}\n'.format(c2, 'O'))
                up.write('\n')

    # gen test
    print("generate test...")
    with codecs.open('./data/test.txt', 'w') as up:
        rows = [each for each in test_df.iloc[:].itertuples()]
        for row in tqdm(rows):
            sentences = get_sentences(row.text)
            up.write('Ж{0}Ж {1}\n'.format(str(row.id), 'O'))
            for sent in sentences:
                for c1 in sent:
                    up.write('{0} {1}\n'.format(c1, 'O'))
                up.write('\n')


def check_brackets(w):
    w = w.rstrip('（')
    w = w.rstrip('(')
    w = w.lstrip(')')
    w = w.lstrip('）')
    cnt_chinese = 0
    cnt_english = 0
    for c in w:
        if c == '（':
            cnt_chinese += 1
        elif c == '）':
            cnt_chinese -= 1
    for c in w:
        if c == '(':
            cnt_english += 1
        elif c == ')':
            cnt_english -= 1

    if cnt_chinese == 0 and cnt_english == 0:
        if w.startswith('（') and w.endswith('）'):
            return w[1:-1]
        if w.startswith('(') and w.endswith(')'):
            return w[1:-1]
        return w

    if cnt_chinese > 0:
        if not w.startswith('（'):
            return w + '）'
        return w[1:]
    if cnt_chinese < 0:
        if not w.endswith('）'):
            return '（' + w
        return w[:-1]
    if cnt_english > 0:
        if not w.startswith('('):
            return w + ')'
        return w[1:]
    if cnt_english < 0:
        if not w.endswith(')'):
            return '(' + w
        return w[:-1]


def check_quotation(w):
    w = w.lstrip('”')
    w = w.lstrip('’')
    w = w.rstrip('“')
    w = w.rstrip('‘')

    cnt_double = 0
    cnt_single = 0
    for c in w:
        if c == '“':
            cnt_double += 1
        elif c == '”':
            cnt_double -= 1
    for c in w:
        if c == '‘':
            cnt_single += 1
        elif c == '’':
            cnt_single -= 1

    if cnt_double == 0 and cnt_single == 0:
        if w.startswith('“') and w.endswith('”'):
            return w[1:-1]
        if w.startswith('‘') and w.endswith('’'):
            return w[1:-1]
        return w

    if cnt_double > 0:
        if not w.startswith('“'):
            return w + '”'
        return w[1:]
    if cnt_double < 0:
        if not w.endswith('”'):
            return '“' + w
        return w[:-1]
    if cnt_single > 0:
        if not w.startswith('‘'):
            return w + '’'
        return w[1:]
    if cnt_single < 0:
        if not w.endswith('’'):
            return '‘' + w
        return w[:-1]


def filter_word(w):
    add_char = {']', '：', '~', '！', '%', '[', '《', '】', ';', ':', '》', '？', '>', '/', '#', '。', '；', '&', '=', '，',
                '【', '@', '、', '|', '大学', '中学', '小学'}
    if w == '':
        return ''

    if re.findall("\\" + "|\\".join(add_char), w):
        return ''

    if 'CEO' in w:
        w = w.replace('CEO', '')
    # if judge_pure_english(w):
    #     return ''

    w = check_brackets(w)
    w = check_quotation(w)
    if w.isnumeric():
        return ''
    if len(w) == 1:
        return ''

    return w


def judge_pure_english(keyword):
    return all(ord(c) < 128 for c in keyword)


def gen_csv(mode='test'):
    predict = codecs.open('./output/label_%s.txt' % mode).read().split('\n\n')
    save_name = './res/%s.csv' % mode
    if os.path.exists(save_name):
        os.remove(save_name)
    res = codecs.open(save_name, 'w')
    res.write('id,unknownEntities\n')
    id = ''
    unknown_entities = set()
    for sent in tqdm(predict):
        sent = sent.split('\n')
        entity = ''
        for each in sent:
            if each == '':
                continue
            tmp_id = re.findall('Ж(.*?)Ж', each)
            if len(tmp_id) == 1:
                if id != '':
                    # unknown_entities = select_candidates(unknown_entities)
                    res.write('{0},{1}\n'.format(id, ';'.join(list(unknown_entities))))
                id = tmp_id[0]
                unknown_entities = set()
                continue
            word, _, tag = each.split()
            if tag == 'B-ORG':
                if entity == '':
                    entity = word
                else:
                    entity = filter_word(entity)
                    if entity != '':
                        unknown_entities.add(entity)
                    entity = ''
            elif tag == 'I-ORG':
                if entity != '':
                    entity += word
            else:
                entity = filter_word(entity)
                if entity != '':
                    unknown_entities.add(entity)
                entity = ''
    # unknown_entities = select_candidates(unknown_entities)
    res.write('{0},{1}\n'.format(id, ';'.join(list(unknown_entities))))
    res.close()


# def select_candidates(unknown_entities):
#     unknown_entities = list(unknown_entities)
#     tmp = sorted(unknown_entities, key=lambda e: len(e))
#     if tmp != []:
#         unknown_entities = []
#         for i in range(len(tmp) - 1):
#             flag = True
#             for j in range(i + 1, len(tmp)):
#                 if tmp[i] in tmp[j]:
#                     flag = False
#                     break
#             if flag:
#                 unknown_entities.append(tmp[i])
#         unknown_entities.append(tmp[-1])
#     return unknown_entities


def completion(candidates, context):
    remove_char = {']', '：', '~', '！', '%', '[', '《', '】', ';', ':', '》', '？', '>', '/', '#', '。', '；', '&', '=',
                   '，',
                   '【', '@', '、', '|', ',', '”', '?'}

    context = context[1] + '。' + context[2]
    tmp = []
    for each in candidates:
        index = context.find(each)
        ex = 1
        if context.count(each) > 1:
            for i in range(1, len(context) - index - len(each)):
                if context.count(each) != context.count(context[index:index + i + len(each)]):
                    ex = i
                    break

            new = context[index:index + ex - 1 + len(each)]
            flag = True
            if len(new) < 22 and len(re.findall("\\" + "|\\".join(remove_char), new)) == 0:
                try:
                    xx = re.findall('(%s.*?)(理财|集团|控股|平台|银行|公司|资本|投资|生态|策略|控股集团)' % each, new)
                    if xx:
                        flag = False
                        new = xx[0][0] + xx[0][1]
                        if context.count(each) == context.count(new):
                            tmp.append(new)
                        else:
                            tmp.append(each)
                            tmp.append(new)
                    else:
                        if ex > 1:
                            print(each, new)
                except:
                    pass

            if flag:
                tmp.append(each)
        else:
            # xx = re.findall('(%s.*?)(理财|集团|控股|平台|银行|公司|资本|投资|生态|策略|控股集团)' % each, context)
            # if xx:
            #     new = xx[0][0] + xx[0][1]
            #     if len(new) < 22 and len(re.findall("\\" + "|\\".join(add_char), new)) == 0:
            #         print(each, new)
            #     each = new
            tmp.append(each)

    tmp = list(set(tmp))

    xx = []
    for w in tmp:
        if w in remove or w in predict_dictionary:
            continue
        xx.append((context.count(w), w))
    xx.sort(key=lambda k: (k[0], len(k[1])), reverse=True)

    res = []
    for i in range(len(xx) - 1):
        if xx[i + 1][0] == xx[i][0] and xx[i + 1][1].startswith(xx[i][1]):
            continue
        res.append(xx[i][1])
    if len(xx) > 0:
        res.append(xx[-1][1])

    return res


def process_data():
    print('process train.csv...')
    with open('./data/old/Train_Data_Hand.csv', 'r', encoding='utf-8') as myFile:
        lines = list(csv.reader(myFile))
        data = []
        for line in lines[1:]:
            line = clean(line)
            data.append(line)

        headers = ['id', 'title', 'text', 'unknownEntities']
        with open('./data/Train_Data.csv', 'w', encoding='utf-8') as f:
            f_csv = csv.writer(f)
            f_csv.writerow(headers)
            f_csv.writerows(data)

    print('process test.csv...')
    with open('./data/old/Test_Data.csv', 'r', encoding='utf-8') as myFile:
        lines = list(csv.reader(myFile))
        data = []
        for line in lines[1:]:
            line = clean(line)
            data.append(line)
        headers = ['id', 'title', 'text']
        with open('./data/Test_Data.csv', 'w', encoding='utf-8') as f:
            f_csv = csv.writer(f)
            f_csv.writerow(headers)
            f_csv.writerows(data)


def clean(line):
    # remove title is the same as text
    if len(line[1]) > 40 and line[2].startswith(line[1][:-9]):
        line[1] = ''
    for i in range(1, 3):
        if line[i] != '':
            line[i] = line[i].replace(",", "，")
            line[i] = line[i].replace("\xa0", "")
            line[i] = line[i].replace("\b", "")
            line[i] = line[i].replace('"', "")
            line[i] = re.sub("\t|\n|\x0b|\x1c|\x1d|\x1e", "", line[i])
            line[i] = line[i].strip()
            line[i] = re.sub('\?\?+', '', line[i])
            line[i] = re.sub('\{IMG:.?.?.?\}', '', line[i])
            line[i] = re.sub('\t|\n', '', line[i])
    return line


def back_process(mode='test'):
    print('after treatment...')
    results = open('./res/%s.csv' % mode).read().split('\n')
    if results[-1] == '':
        results = results[:-1]
    res = codecs.open('./res/%s_completion.csv' % mode, 'w')
    res.write('id,unknownEntities\n')

    with open('./data/old/Test_Data.csv', 'r', encoding='utf-8') as myFile:
        lines = list(csv.reader(myFile))
        if lines[-1] == '':
            lines = lines[:-1]
        for i in range(1, len(lines)):
            id, candidates = results[i].split(',')
            candidates = candidates.split(';')
            entity = completion(candidates, lines[i])
            res.write('{0},{1}\n'.format(id, ';'.join(entity)))
    res.close()


def remove_entity(mode='test'):
    print('Removing entities...')
    results = open('./res/%s_completion.csv' % mode).read().split('\n')
    if results[-1] == '':
        results = results[:-1]
    res = codecs.open('./res/%s_completion.csv' % mode, 'w')
    res.write('id,unknownEntities\n')
    for line in results[1:]:
        if ',' in line:
            id, entities = line.split(',')
            entities = entities.split(';')
            tmp = [each for each in entities if each not in remove]
            res.write('%s,%s\n' % (id, ';'.join(tmp)))
        else:
            res.write('%s\n' % line)


if __name__ == "__main__":
    # process_data()
    # gen_bio()
    # gen_csv()
    back_process()
    # remove_entity()
