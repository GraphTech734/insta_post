let agendamentoAtivo = false;

function abrirConfiguracoes() {
    var configPanel = document.getElementById('configPanel');
    if (configPanel.style.display === 'none') {
        configPanel.style.display = 'block';
    } else {
        configPanel.style.display = 'none';
    }
}

function alternarExclusao() {
    fetch('/configuracoes', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json'
        }
    })
    .then(response => response.json())
    .then(data => {
        if (data.status === 'success') {
            alert('Exclusão de mídias ' + (data.excluir_apos_upload ? 'ativada' : 'desativada'));
        }
    });
}

function iniciarPararAgendamento() {
    if (agendamentoAtivo) {
        pararAgendamento();
    } else {
        iniciarAgendamento();
    }
}

function iniciarAgendamento() {
    var mediaFolder = document.getElementById('media_folder').files;
    var postInterval = document.getElementById('post_interval').value;
    var hashtags = document.getElementById('hashtags').value;

    if (mediaFolder.length === 0) {
        alert('Por favor, selecione arquivos de mídia.');
        return;
    }

    var formData = new FormData();
    for (var i = 0; i < mediaFolder.length; i++) {
        formData.append('media_files', mediaFolder[i]);
    }
    formData.append('post_interval', postInterval);
    formData.append('hashtags', hashtags);

    showLoading('Iniciando postagens...');

    fetch('/agendar', {
        method: 'POST',
        body: formData
    })
    .then(response => response.json())
    .then(data => {
        hideLoading();
        if (data.status === 'success') {
            agendamentoAtivo = true;
            document.getElementById('toggleButton').textContent = 'Parar Agendamento';
            alert('Agendamento iniciado');
        } else {
            alert('Erro ao iniciar agendamento: ' + data.message);
        }
    })
    .catch(error => {
        hideLoading();
        console.error('Erro:', error);
        alert('Erro ao iniciar agendamento');
    });
}

function pararAgendamento() {
    showLoading('Parando postagens...');

    fetch('/parar', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json'
        }
    })
    .then(response => response.json())
    .then(data => {
        hideLoading();
        if (data.status === 'success') {
            agendamentoAtivo = false;
            document.getElementById('toggleButton').textContent = 'Iniciar Agendamento';
            alert('Agendamento parado');
        } else {
            alert('Erro ao parar agendamento: ' + data.message);
        }
    })
    .catch(error => {
        hideLoading();
        console.error('Erro:', error);
        alert('Erro ao parar agendamento');
    });
}

function showLoading(message) {
    var loadingOverlay = document.getElementById('loadingOverlay');
    var loadingMessage = document.getElementById('loadingMessage');
    loadingMessage.textContent = message;
    loadingOverlay.style.display = 'flex';
}

function hideLoading() {
    var loadingOverlay = document.getElementById('loadingOverlay');
    loadingOverlay.style.display = 'none';
}


    document.addEventListener('DOMContentLoaded', () => {
        const iconeAjuda = document.getElementById('iconeAjuda');
        const mensagemAjuda = document.getElementById('mensagemAjuda');

        if (iconeAjuda && mensagemAjuda) {
            iconeAjuda.addEventListener('click', () => {
                mensagemAjuda.style.display = mensagemAjuda.style.display === 'block' ? 'none' : 'block';
            });

            document.addEventListener('click', (event) => {
                if (mensagemAjuda.style.display === 'block' && !iconeAjuda.contains(event.target) && !mensagemAjuda.contains(event.target)) {
                    mensagemAjuda.style.display = 'none';
                }
            });
        }
    });
