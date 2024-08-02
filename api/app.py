from flask import Flask, render_template, request, redirect, url_for, session, jsonify
import os
import json
import schedule
import time
from instagrapi import Client
from threading import Thread
import tempfile
from werkzeug.utils import secure_filename

app = Flask(__name__)
app.secret_key = os.getenv('SECRET_KEY', 'sua_chave_secreta')  # Use variáveis de ambiente para a chave secreta
config_file = 'config.json'


# Carrega as configurações salvas
def carregar_configuracoes():
    if os.path.exists(config_file):
        with open(config_file, 'r') as file:
            return json.load(file)
    else:
        return {"tema_atual": "light", "excluir_apos_upload": True, "login_info": {}, "postadas": []}


# Salva as configurações atuais
def salvar_configuracoes(configuracoes):
    with open(config_file, 'w') as file:
        json.dump(configuracoes, file)


configuracoes = carregar_configuracoes()
excluir_apos_upload = configuracoes.get('excluir_apos_upload', True)
login_info = configuracoes.get('login_info', {})
postadas = configuracoes.get('postadas', [])
agendamento_ativo = False
thread_agendamento = None


# Função para obter informações atualizadas do usuário
def atualizar_info_usuario():
    cl = Client()
    try:
        cl.login(login_info['usuario'], login_info['senha'])
        user_info = cl.account_info()
        session['user_info'] = {
            'username': user_info.username,
            'full_name': user_info.full_name,
            'biography': user_info.biography,
        }
        salvar_configuracoes(configuracoes)  # Salvar informações atualizadas nas configurações
    except Exception as e:
        print(f'Erro ao atualizar informações do usuário: {str(e)}')


@app.route('/')
def login():
    return render_template('login.html')


@app.route('/login', methods=['POST'])
def do_login():
    usuario = request.form['usuario']
    senha = request.form['senha']
    login_info['usuario'] = usuario
    login_info['senha'] = senha
    configuracoes['login_info'] = login_info
    salvar_configuracoes(configuracoes)

    cl = Client()
    try:
        cl.login(usuario, senha)
        atualizar_info_usuario()  # Atualizar informações do usuário ao fazer login
        session['logged_in'] = True
        return jsonify({'status': 'success'})
    except Exception as e:
        if 'challenge_required' in str(e):
            session['usuario'] = usuario
            session['senha'] = senha
            return jsonify({'status': '2fa'})
        else:
            return jsonify({'status': 'error', 'message': 'Usuário ou senha incorreto'})


@app.route('/2fa', methods=['POST'])
def do_2fa():
    codigo = request.form['codigo']
    usuario = session.get('usuario')
    senha = session.get('senha')
    cl = Client()
    try:
        cl.login(usuario, senha, verification_code=codigo)
        login_info['usuario'] = usuario
        login_info['senha'] = senha
        configuracoes['login_info'] = login_info
        salvar_configuracoes(configuracoes)
        atualizar_info_usuario()  # Atualizar informações do usuário ao fazer login
        session['logged_in'] = True
        return redirect(url_for('main'))
    except Exception as e:
        return str(e)


@app.route('/main')
def main():
    if 'logged_in' in session and session['logged_in']:
        user_info = session.get('user_info', {})
        return render_template('main.html', user_info=user_info)
    else:
        return redirect(url_for('login'))


@app.route('/configuracoes', methods=['POST'])
def configuracoes_api():
    global excluir_apos_upload
    excluir_apos_upload = not excluir_apos_upload
    configuracoes['excluir_apos_upload'] = excluir_apos_upload
    salvar_configuracoes(configuracoes)
    return jsonify({'status': 'success', 'excluir_apos_upload': excluir_apos_upload})


@app.route('/agendar', methods=['POST'])
def agendar():
    print("Recebendo solicitação de agendamento")
    post_interval = int(request.form['post_interval'])
    interval_type = request.form.get('interval_type', 'minutes')  # Padrão para 'minutes' se não estiver presente
    hashtags = request.form.get('hashtags', '').strip()
    media_files = request.files.getlist('media_files')

    temp_dir = tempfile.mkdtemp()
    saved_files = []

    for media_file in media_files:
        filename = secure_filename(media_file.filename)
        if filename not in configuracoes['postadas']:
            file_path = os.path.join(temp_dir, filename)
            media_file.save(file_path)
            saved_files.append(file_path)

    print(f"Arquivos salvos: {saved_files}")

    # Postagem imediata
    post_media(login_info['usuario'], login_info['senha'], saved_files, hashtags)

    global agendamento_ativo
    agendamento_ativo = True  # Defina como True antes de iniciar a thread
    thread_agendamento = Thread(target=agendar_postagens, args=(
    login_info['usuario'], login_info['senha'], saved_files, post_interval, interval_type, hashtags))
    thread_agendamento.start()

    print("Agendamento iniciado")
    return jsonify({'status': 'success'})


@app.route('/parar', methods=['POST'])
def parar():
    global agendamento_ativo
    agendamento_ativo = False
    if thread_agendamento is not None:
        thread_agendamento.join()
    print("Agendamento parado")
    return jsonify({'status': 'success'})


def post_media(instagram_user, instagram_pass, media_files, hashtags):
    global excluir_apos_upload
    cl = Client()
    try:
        cl.login(instagram_user, instagram_pass)
    except Exception as e:
        return str(e)

    if media_files:
        media_file = media_files.pop(0)
        filename = os.path.basename(media_file)
        caption = hashtags if hashtags else ""
        try:
            if media_file.lower().endswith(('.png', '.jpg', '.jpeg')):
                cl.photo_upload(media_file, caption, extra_data={"custom_accessibility_caption": "alt text example",
                                                                 "like_and_view_counts_disabled": 1,
                                                                 "disable_comments": 1})
            elif media_file.lower().endswith(('.mp4', '.mov')):
                cl.video_upload(media_file, caption)
            configuracoes['postadas'].append(filename)
            salvar_configuracoes(configuracoes)

            if excluir_apos_upload:
                os.remove(media_file)

        except Exception as e:
            print(f'Erro ao postar mídia: {str(e)}')


def agendar_postagens(instagram_user, instagram_pass, media_files, post_interval, interval_type, hashtags):
    global agendamento_ativo
    if interval_type == 'hours':
        schedule.every(post_interval).hours.do(post_media, instagram_user=instagram_user, instagram_pass=instagram_pass,
                                               media_files=media_files, hashtags=hashtags)
    else:
        schedule.every(post_interval).minutes.do(post_media, instagram_user=instagram_user,
                                                 instagram_pass=instagram_pass, media_files=media_files,
                                                 hashtags=hashtags)

    while agendamento_ativo:
        schedule.run_pending()
        time.sleep(1)


if __name__ == '__main__':
    app.run(debug=True)
