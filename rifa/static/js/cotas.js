// Funções para cotas na página de detalhes da rifa
function somarCotas(qtd) {
  let input = document.getElementById("input-cotas") || document.getElementById("quantidade");
  let atual = parseInt(input.value) || 0;
  let novo = atual + Number(qtd);
  if (novo < 1) novo = 1;
  input.value = novo;
  atualizarTotal();
}

function ajustarQtd(delta) {
  let input = document.getElementById("input-cotas") || document.getElementById("quantidade");
  let atual = parseInt(input.value) || 0;
  let novo = Math.max(1, atual + delta);
  input.value = novo;
  atualizarTotal();
}

function selecionarCotas(qtd) {
  let novo = Math.max(1, Number(qtd));
  let input = document.getElementById("input-cotas") || document.getElementById("quantidade");
  input.value = novo;
  atualizarTotal();
}

function atualizarTotal() {
  let input = document.getElementById("quantidade");
  let inputEl = document.getElementById("input-cotas") || document.getElementById("quantidade");
  let totalCotas = parseInt(inputEl.value) || 0;
  document.getElementById("totalSelecionado").innerText = `Total selecionado: ${totalCotas}`;
  let valorUnitario = parseFloat(document.getElementById("btnAdquirir")?.dataset?.valorUnitario || document.getElementById('input-cotas')?.dataset?.preco || '0');
  let total = (totalCotas * valorUnitario).toFixed(2).replace('.',',');
  const btn = document.getElementById("btnAdquirir");
  if (btn) btn.innerHTML = `✅ Adquirir Bilhete — R$ ${total}`;
}

document.addEventListener("DOMContentLoaded", function() {
  atualizarTotal();
});
