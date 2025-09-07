// SOLUÇÃO DEFINITIVA: Modificar openPaymentModal para aceitar 3 parâmetros
function openPaymentModal(valorTotal, quantidade, rifaId) {
  console.log('PAYMENT.JS - Modal aberto com:', { valorTotal, quantidade, rifaId });
  
  const backdrop = document.getElementById('paymentBackdrop');
  if (!backdrop) return;
  
  // CORREÇÃO: Salvar todos os dados nos campos hidden
  document.getElementById('hiddenRifaId').value = rifaId || '';
  document.getElementById('hiddenQuantidade').value = quantidade || '';
  document.getElementById('hiddenValorTotal').value = valorTotal || '';
  
  console.log('PAYMENT.JS - Dados salvos:', {
    rifaId: document.getElementById('hiddenRifaId').value,
    quantidade: document.getElementById('hiddenQuantidade').value,
    valorTotal: document.getElementById('hiddenValorTotal').value
  });
  
  // Atualizar interface
  const span = document.getElementById('payValorTotal');
  if (span) { 
    span.textContent = valorTotal || span.textContent; 
  }
  
  const qtdSpan = document.getElementById('payQuantidade');
  if (qtdSpan) {
    qtdSpan.textContent = quantidade || '1';
  }
  
  backdrop.style.display = 'flex';
  document.body.style.overflow = 'hidden';
  
  const cpf = document.getElementById('payCpf');
  // reset estado usuário
  document.getElementById('payUserBox')?.setAttribute('style','display:none;background:#222;border:1px solid #333;');
  document.getElementById('payUserNotFound')?.setAttribute('style','display:none;font-size:.85rem;');
  const btnReservar = document.getElementById('btnReservar') || document.getElementById('btnPagar');
  btnReservar && (btnReservar.disabled = true);
  const btnOutro = document.getElementById('btnOutroCadastro');
  btnOutro && (btnOutro.style.display = 'none');
  cpf && (cpf.value = '');
  cpf && cpf.focus();
}

function closePaymentModal(){
  const backdrop = document.getElementById('paymentBackdrop');
  if (!backdrop) return; 
  backdrop.style.display = 'none';
  document.body.style.overflow = '';
}

// Fecha ao clicar fora
window.addEventListener('click', e => {
  const backdrop = document.getElementById('paymentBackdrop');
  if (e.target === backdrop) { 
    closePaymentModal(); 
  }
});

// Esc
window.addEventListener('keydown', e => { 
  if (e.key === 'Escape') closePaymentModal(); 
});

// Máscara CPF
const cpfInputHandler = e => {
  let v = e.target.value.replace(/\D/g,'').slice(0,11);
  let f = '';
  if (v.length > 0) f = v.slice(0,3);
  if (v.length >= 4) f += '.' + v.slice(3,6);
  if (v.length >= 7) f += '.' + v.slice(6,9);
  if (v.length >= 10) f += '-' + v.slice(9,11);
  e.target.value = f;
  if (v.length === 11) {
    buscarUsuarioPorCpf(f);
  } else {
    // limpando estado
    document.getElementById('payUserBox')?.setAttribute('style','display:none;background:#222;border:1px solid #333;');
    document.getElementById('payUserNotFound')?.setAttribute('style','display:none;font-size:.85rem;');
    const btnReservar = document.getElementById('btnReservar') || document.getElementById('btnPagar');
    btnReservar && (btnReservar.disabled = true);
  }
};

window.addEventListener('DOMContentLoaded', () => {
  const cpf = document.getElementById('payCpf');
  cpf && ['input','paste'].forEach(ev => cpf.addEventListener(ev, cpfInputHandler));
});

// CORREÇÃO: Função de submit modificada para usar dados dos campos hidden
function submitReserva(ev) {
  ev.preventDefault();
  
  console.log('SUBMIT RESERVA CHAMADO');
  
  // Ler dados dos campos hidden
  const rifaId = document.getElementById('hiddenRifaId').value;
  const quantidade = document.getElementById('hiddenQuantidade').value;
  
  console.log('DADOS DOS HIDDEN FIELDS:', { rifaId, quantidade });
  
  if (!rifaId || !quantidade) {
    alert('Erro: Dados do pedido perdidos. Recarregue a página.');
    return false;
  }

  const cpf = document.getElementById('payCpf').value.trim();
  if (cpf.length < 14) {
    alert('CPF inválido.');
    return false;
  }

  const btn = document.getElementById('btnReservar') || document.getElementById('btnPagar');
  btn && (btn.disabled = true, btn.textContent = 'Gerando PIX...');

  const formData = new FormData();
  formData.append('rifa_id', rifaId);
  formData.append('cpf', cpf);
  formData.append('quantidade', quantidade);

  console.log('ENVIANDO PARA SERVIDOR:', { rifa_id: rifaId, cpf: cpf, quantidade: quantidade });

  fetch('/api/criar-pedido/', {
    method: 'POST', 
    body: formData, 
    headers: {
      'X-Requested-With': 'XMLHttpRequest',
      'X-CSRFToken': getCsrfToken()
    }
  })
  .then(r => r.json())
  .then(data => {
    console.log('RESPOSTA DO SERVIDOR:', data);
    
    if (data.success && data.redirect) {
      // Se ganhou prêmios, informa antes de redirecionar
      if (Array.isArray(data.premios_ganhos) && data.premios_ganhos.length) {
        try {
          const msg = data.premios_ganhos.map(p => `Número premiado ${String(p.numero).padStart(6,'0')} (R$ ${Number(p.valor).toFixed(2)})`).join('\n');
          alert('🎉 Você ACABA DE GANHAR!\n' + msg + '\nSeu prêmio já está registrado.');
        } catch(_e) {}
      }
      // Redireciona o usuário para a página de pagamento onde o QR e o código serão exibidos
      btn && (btn.textContent = 'Redirecionando...');
      window.location.href = data.redirect;
    } else {
      alert(data.error || 'Falha ao criar pedido');
      btn && (btn.disabled = false, btn.textContent = 'Reservar bilhetes');
    }
  })
  .catch(err => {
    console.error(err);
    alert('Erro inesperado.');
    btn && (btn.disabled = false, btn.textContent = 'Reservar bilhetes');
  });
  return false;
}

// NOVA FUNÇÃO: processarPagamento para compatibilidade com o modal atual
function processarPagamento() {
  console.log('PROCESSAR PAGAMENTO CHAMADO');
  return submitReserva({ preventDefault: () => {} });
}

// NOVA FUNÇÃO: verificarCpf para compatibilidade
function verificarCpf(event) {
  event.preventDefault();
  const cpf = document.getElementById('payCpf').value.trim();
  if (cpf.length === 14) {
    buscarUsuarioPorCpf(cpf);
  }
  return false;
}

async function buscarUsuarioPorCpf(cpfFormatado) {
  try {
    const url = `/api/usuario-por-cpf/?cpf=${encodeURIComponent(cpfFormatado)}`;
    const resp = await fetch(url, {headers: {'Accept': 'application/json'}});
    const data = await resp.json();
    const box = document.getElementById('payUserBox');
    const notFound = document.getElementById('payUserNotFound');
    const btnReservar = document.getElementById('btnReservar') || document.getElementById('btnPagar');
    const btnOutro = document.getElementById('btnOutroCadastro');
    
    if (data.found) {
      if (box) {
        box.style.display = 'block';
        document.getElementById('payUserNome').textContent = data.nome || '—';
        document.getElementById('payUserEmail').textContent = data.email || '';
        document.getElementById('payUserTelefone').textContent = data.telefone || '';
      }
      notFound && (notFound.style.display = 'none');
      btnReservar && (btnReservar.disabled = false);
      btnOutro && (btnOutro.style.display = 'block');
    } else {
      box && (box.style.display = 'none');
      if (notFound) { 
        notFound.style.display = 'block'; 
        notFound.textContent = data.message || 'Não encontrado.'; 
      }
      btnReservar && (btnReservar.disabled = true);
      btnOutro && (btnOutro.style.display = 'none');
    }
  } catch(err) {
    console.error('Erro ao buscar CPF', err);
  }
}

function resetarCpfPagamento() {
  const cpf = document.getElementById('payCpf');
  cpf && (cpf.value = '');
  document.getElementById('payUserBox')?.setAttribute('style','display:none;background:#222;border:1px solid #333;');
  document.getElementById('payUserNotFound')?.setAttribute('style','display:none;font-size:.85rem;');
  const btnReservar = document.getElementById('btnReservar') || document.getElementById('btnPagar');
  btnReservar && (btnReservar.disabled = true);
  const btnOutro = document.getElementById('btnOutroCadastro');
  btnOutro && (btnOutro.style.display = 'none');
  cpf && cpf.focus();
}

// Função para obter CSRF Token
function getCsrfToken() {
  return document.querySelector('[name=csrfmiddlewaretoken]')?.value || '';
}