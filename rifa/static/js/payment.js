function openPaymentModal(total){
  const backdrop=document.getElementById('paymentBackdrop');
  if(!backdrop) return; 
  const span=document.getElementById('payValorTotal');
  if(span){ span.textContent= total || span.textContent; }
  backdrop.style.display='flex';
  document.body.style.overflow='hidden';
  const cpf=document.getElementById('payCpf');
  // reset estado usuário
  document.getElementById('payUserBox')?.setAttribute('style','display:none;background:#222;border:1px solid #333;');
  document.getElementById('payUserNotFound')?.setAttribute('style','display:none;font-size:.85rem;');
  const btnReservar=document.getElementById('btnReservar');
  btnReservar && (btnReservar.disabled=true);
  const btnOutro=document.getElementById('btnOutroCadastro');
  btnOutro && (btnOutro.style.display='none');
  cpf && (cpf.value='');
  cpf && cpf.focus();
}
function closePaymentModal(){
  const backdrop=document.getElementById('paymentBackdrop');
  if(!backdrop) return; 
  backdrop.style.display='none';
  document.body.style.overflow='';
}
// Fecha ao clicar fora
window.addEventListener('click',e=>{
  const backdrop=document.getElementById('paymentBackdrop');
  if(e.target===backdrop){ closePaymentModal(); }
});
// Esc
window.addEventListener('keydown',e=>{ if(e.key==='Escape') closePaymentModal(); });
// Máscara CPF
const cpfInputHandler=e=>{
  let v=e.target.value.replace(/\D/g,'').slice(0,11);
  let f='';
  if(v.length>0) f=v.slice(0,3);
  if(v.length>=4) f+='.'+v.slice(3,6);
  if(v.length>=7) f+='.'+v.slice(6,9);
  if(v.length>=10) f+='-'+v.slice(9,11);
  e.target.value=f;
  if(v.length===11){
    buscarUsuarioPorCpf(f);
  } else {
    // limpando estado
    document.getElementById('payUserBox')?.setAttribute('style','display:none;background:#222;border:1px solid #333;');
    document.getElementById('payUserNotFound')?.setAttribute('style','display:none;font-size:.85rem;');
    const btnReservar=document.getElementById('btnReservar');
    btnReservar && (btnReservar.disabled=true);
  }
};
window.addEventListener('DOMContentLoaded',()=>{
  const cpf=document.getElementById('payCpf');
  cpf && ['input','paste'].forEach(ev=>cpf.addEventListener(ev,cpfInputHandler));
});
// Simulação submit (futuro integrar backend)
function submitReserva(ev){
  ev.preventDefault();
  const cpf=document.getElementById('payCpf').value.trim();
  if(cpf.length<14){
    alert('CPF inválido.');
    return false;
  }
  const qtdInput=document.getElementById('input-cotas');
  const qtd = parseInt(qtdInput?.value||'0',10);
  if(!qtd || qtd<1){ alert('Quantidade inválida.'); return false; }
  const btn=document.getElementById('btnReservar');
  btn && (btn.disabled=true, btn.textContent='Gerando PIX...');
  // Descobrir rifa_id a partir de data attribute (adicionar no template se necessário)
  const rifaIdEl=document.querySelector('[data-rifa-id]');
  const rifaId= rifaIdEl? rifaIdEl.getAttribute('data-rifa-id'): (window.RIFA_ID||'');
  const formData=new FormData();
  formData.append('rifa_id', rifaId);
  formData.append('cpf', cpf);
  formData.append('quantidade', qtd);
  fetch('/api/criar-pedido/', {method:'POST', body:formData, headers:{'X-Requested-With':'XMLHttpRequest'}})
    .then(r=>r.json())
    .then(data=>{
      if(data.success && data.redirect){
        // Checa prêmios ganhos
        if(Array.isArray(data.premios_ganhos) && data.premios_ganhos.length){
          try {
            const msg = data.premios_ganhos.map(p=>`Número premiado ${String(p.numero).padStart(6,'0')} (R$ ${Number(p.valor).toFixed(2)})`).join('\n');
            alert('🎉 Você ACABA DE GANHAR!\n' + msg + '\nSeu prêmio já está registrado.');
          } catch(_e){}
        }
        window.location.href=data.redirect;
      } else {
        alert(data.error||'Falha ao criar pedido');
        btn && (btn.disabled=false, btn.textContent='Reservar bilhetes');
      }
    })
    .catch(err=>{
      console.error(err);
      alert('Erro inesperado.');
      btn && (btn.disabled=false, btn.textContent='Reservar bilhetes');
    });
  return false;
}

async function buscarUsuarioPorCpf(cpfFormatado){
  try{
    const url=`/api/usuario-por-cpf/?cpf=${encodeURIComponent(cpfFormatado)}`;
    const resp=await fetch(url,{headers:{'Accept':'application/json'}});
    const data=await resp.json();
    const box=document.getElementById('payUserBox');
    const notFound=document.getElementById('payUserNotFound');
    const btnReservar=document.getElementById('btnReservar');
    const btnOutro=document.getElementById('btnOutroCadastro');
    if(data.found){
      if(box){
        box.style.display='block';
        document.getElementById('payUserNome').textContent=data.nome || '—';
        document.getElementById('payUserEmail').textContent=data.email || '';
        document.getElementById('payUserTelefone').textContent=data.telefone || '';
      }
      notFound && (notFound.style.display='none');
      btnReservar && (btnReservar.disabled=false);
      btnOutro && (btnOutro.style.display='block');
    } else {
      box && (box.style.display='none');
      if(notFound){ notFound.style.display='block'; notFound.textContent=data.message || 'Não encontrado.'; }
      btnReservar && (btnReservar.disabled=true);
      btnOutro && (btnOutro.style.display='none');
    }
  }catch(err){
    console.error('Erro ao buscar CPF',err);
  }
}

function resetarCpfPagamento(){
  const cpf=document.getElementById('payCpf');
  cpf && (cpf.value='');
  document.getElementById('payUserBox')?.setAttribute('style','display:none;background:#222;border:1px solid #333;');
  document.getElementById('payUserNotFound')?.setAttribute('style','display:none;font-size:.85rem;');
  const btnReservar=document.getElementById('btnReservar');
  btnReservar && (btnReservar.disabled=true);
  const btnOutro=document.getElementById('btnOutroCadastro');
  btnOutro && (btnOutro.style.display='none');
  cpf && cpf.focus();
}
