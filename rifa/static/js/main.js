document.addEventListener("DOMContentLoaded", () => {
  // Funções auxiliares
  const toggleScroll = (enable) => {
    document.body.style.overflow = enable ? '' : 'hidden';
  };

  const updateInputCotas = (valor) => {
    const input = document.getElementById('input-cotas');
    if (input) input.value = valor;
  };
  
  // Garante que mudanças programáticas também disparem o evento 'input' para atualizar totais
  const dispatchInputUpdate = (valor) => {
    const input = document.getElementById('input-cotas');
    if (!input) return;
    input.value = String(valor);
    try { input.dispatchEvent(new Event('input', { bubbles: true })); } catch(e) { /* fallback */ }
  };

  // Função para mostrar feedback visual
  const showFeedback = (message, type = 'success') => {
    const feedback = document.createElement('div');
    feedback.className = `feedback-toast ${type}`;
    feedback.textContent = message;
    feedback.style.cssText = `
      position: fixed;
      top: 20px;
      right: 20px;
      background: ${type === 'success' ? 'var(--success)' : 'var(--danger)'};
      color: white;
      padding: 12px 20px;
      border-radius: 8px;
      z-index: 9999;
      opacity: 0;
      transform: translateX(100%);
      transition: all 0.3s ease;
      box-shadow: 0 4px 12px rgba(0,0,0,0.3);
    `;
    
    document.body.appendChild(feedback);
    
    setTimeout(() => {
      feedback.style.opacity = '1';
      feedback.style.transform = 'translateX(0)';
    }, 100);
    
    setTimeout(() => {
      feedback.style.opacity = '0';
      feedback.style.transform = 'translateX(100%)';
      setTimeout(() => {
        if (document.body.contains(feedback)) {
          document.body.removeChild(feedback);
        }
      }, 300);
    }, 3000);
  };

  // MENU LATERAL MELHORADO
  const btnMenu = document.getElementById("btn-menu");
  const btnFecharMenu = document.getElementById("btn-fechar-menu");
  const menuLateral = document.getElementById("menu-lateral");
  let overlay = null;

  if (btnMenu && menuLateral) {
    // Criar overlay se não existir
    if (!overlay) {
      overlay = document.createElement('div');
      overlay.className = 'menu-overlay';
      document.body.appendChild(overlay);
    }

    btnMenu.addEventListener("click", () => {
      menuLateral.classList.toggle("open");
      
      if (menuLateral.classList.contains("open")) {
        overlay.classList.add("active");
        toggleScroll(false);
      } else {
        overlay.classList.remove("active");
        toggleScroll(true);
      }
    });

    if (btnFecharMenu) {
      btnFecharMenu.addEventListener("click", () => {
        menuLateral.classList.remove("open");
        overlay.classList.remove("active");
        toggleScroll(true);
      });
    }

    // Fechar menu ao clicar no overlay
    overlay.addEventListener("click", () => {
      menuLateral.classList.remove("open");
      overlay.classList.remove("active");
      toggleScroll(true);
    });
  }

  // MODAL DE LOGIN
  const btnLoginMenu = document.getElementById("btnLoginMenu");
  const loginModal = document.getElementById("loginModal");

  if (btnLoginMenu && loginModal) {
    btnLoginMenu.addEventListener("click", () => {
      loginModal.style.display = "flex";
      toggleScroll(false);
      if (menuLateral) menuLateral.classList.remove("open");
    });

    // Fecha modal clicando fora do conteúdo
    loginModal.addEventListener("click", (e) => {
      if (e.target === loginModal) {
        loginModal.style.display = "none";
        toggleScroll(true);
      }
    });
  }

  // CEP - AUTO PREENCHIMENTO
  const cepInput = document.getElementById("cep");
  if (cepInput) {
    cepInput.addEventListener("input", function () {
      const cep = this.value.replace(/\D/g, "");
      if (cep.length === 8) {
        fetch(`https://viacep.com.br/ws/${cep}/json/`)
          .then((res) => res.json())
          .then((data) => {
            if (!data.erro) {
              const logradouro = document.getElementById("logradouro");
              const bairro = document.getElementById("bairro");
              const cidade = document.getElementById("cidade");
              const ufSelect = document.getElementById("uf");

              if (!(logradouro && bairro && cidade && ufSelect)) {
                console.error("Alguns campos de endereço não foram encontrados.");
                return;
              }

              logradouro.value = data.logradouro || "";
              bairro.value = data.bairro || "";
              cidade.value = data.localidade || "";

              for (let i = 0; i < ufSelect.options.length; i++) {
                if (ufSelect.options[i].value === data.uf) {
                  ufSelect.selectedIndex = i;
                  break;
                }
              }
            } else {
              alert("CEP não encontrado.");
            }
          })
          .catch((error) => {
            console.error("Erro ao buscar o CEP:", error);
            alert("Erro ao buscar o CEP. Verifique sua conexão.");
          });
      }
    });
  }

  // FORMULÁRIO - VALIDAÇÃO
  const form = document.querySelector("form");
  if (form) {
    form.addEventListener("submit", function (e) {
      const senha = document.getElementById("senha")?.value;
      const senha2 = document.getElementById("senha2")?.value;
      const telefone = document.getElementById("telefone")?.value;
      const confirmaTelefone = document.getElementById("confirmaTelefone")?.value;

      if (senha && senha2 && senha !== senha2) {
        alert("As senhas não coincidem.");
        e.preventDefault();
        return;
      }

      if (telefone && confirmaTelefone && telefone !== confirmaTelefone) {
        alert("Os telefones não coincidem.");
        e.preventDefault();
        return;
      }

      const loading = document.getElementById("loading");
      if (loading) loading.style.display = "block";
    });
  }

  // MINI ABA DE COTAS (RIFA) - DELEGAÇÃO DE EVENTOS
  document.body.addEventListener("click", function (e) {
    // Botões de cotas rápidas
    if (e.target.classList.contains("btn-cotas")) {
      document.querySelectorAll(".btn-cotas").forEach((b) => b.classList.remove("active"));
      e.target.classList.add("active");
      const valor = parseInt(e.target.dataset.valor, 10);
      dispatchInputUpdate(valor);
    }

    // Botão +
    if (e.target.id === "btn-plus") {
      const input = document.getElementById("input-cotas");
      if (input) {
        const valor = parseInt(input.value, 10) || 0;
          dispatchInputUpdate(valor + 1);
        document.querySelectorAll(".btn-cotas").forEach((b) => b.classList.remove("active"));
      }
    }

    // Botão -
    if (e.target.id === "btn-minus") {
      const input = document.getElementById("input-cotas");
      if (input) {
        let valor = parseInt(input.value, 10);
        if (isNaN(valor) || valor <= 1) {
          valor = 1;
        } else {
          valor = valor - 1;
        }
        dispatchInputUpdate(valor);
        document.querySelectorAll(".btn-cotas").forEach((b) => b.classList.remove("active"));
      }
    }
  });
});
