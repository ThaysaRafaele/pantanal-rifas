(function() {
  function getCookie(name) {
    var value = "; " + document.cookie;
    var parts = value.split("; " + name + "=");
    if (parts.length == 2) return parts.pop().split(";").shift();
  }

  function exibirResultados(data) {
    var resultDiv = document.getElementById('resultados');
    
    if (data.status === 'success') {
      var html = '<div class="alert alert-success mt-3">✅ Encontrados ' + data.numeros.length + ' número(s)</div>';
      
      var rifas = {};
      for (var i = 0; i < data.numeros.length; i++) {
        var n = data.numeros[i];
        if (!rifas[n.rifa_titulo]) rifas[n.rifa_titulo] = [];
        rifas[n.rifa_titulo].push(n);
      }
      
      for (var titulo in rifas) {
        var nums = rifas[titulo];
        html += '<div class="card mb-3"><div class="card-header"><h6 class="mb-0"><strong>Rifa:</strong> ' + titulo + '</h6></div><div class="card-body">';
        
        for (var j = 0; j < nums.length; j++) {
          var num = nums[j];
          var badge = num.status === 'Pago' ? 'success' : 'warning';
          
          html += '<div class="border rounded p-2 mb-2"><div class="row align-items-center">';
          html += '<div class="col-auto"><span class="badge bg-primary fs-6">' + num.numero + '</span></div>';
          html += '<div class="col"><span class="badge bg-' + badge + '">' + num.status + '</span>';
          
          if (num.status === 'Reservado' && num.tempo_restante > 0) {
            var h = Math.floor(num.tempo_restante / 3600);
            var m = Math.floor((num.tempo_restante % 3600) / 60);
            html += '<br><small class="text-warning">⏰ ' + h + 'h ' + m + 'min</small>';
          }
          
          html += '</div>';
          
          if (num.status === 'Reservado' && num.rifa_id && !num.expirado) {
            html += '<div class="col-auto"><button class="btn btn-success btn-sm" onclick="window.location.href=\'/rifa/' + num.rifa_id + '/\'">💳 Pagar</button></div>';
          }
          
          html += '</div></div>';
        }
        
        html += '</div></div>';
      }
      
      resultDiv.innerHTML = html;
    } else {
      resultDiv.innerHTML = '<div class="alert alert-warning mt-3">❌ ' + (data.message || 'Nenhum número encontrado') + '</div>';
    }
  }

  document.getElementById('btnBuscarCpf').onclick = function() {
    var cpf = document.getElementById('inputCpf').value.trim();
    var resultDiv = document.getElementById('resultados');
    
    if (!cpf) {
      resultDiv.innerHTML = '<div class="alert alert-warning mt-3">⚠️ Digite o CPF</div>';
      return;
    }
    
    resultDiv.innerHTML = '<div class="alert alert-info mt-3">🔄 Buscando...</div>';
    
    var fd = new FormData();
    fd.append('cpf', cpf);
    
    fetch('/buscar-pedidos-cpf/', {
      method: 'POST',
      body: fd,
      headers: {'X-CSRFToken': getCookie('csrftoken')}
    })
    .then(function(r) { return r.json(); })
    .then(exibirResultados)
    .catch(function() {
      resultDiv.innerHTML = '<div class="alert alert-danger mt-3">❌ Erro de conexão</div>';
    });
  };

  document.getElementById('btnBuscarTelefone').onclick = function() {
    var tel = document.getElementById('inputTelefone').value.trim();
    var resultDiv = document.getElementById('resultados');
    
    if (!tel) {
      resultDiv.innerHTML = '<div class="alert alert-warning mt-3">⚠️ Digite o telefone</div>';
      return;
    }
    
    resultDiv.innerHTML = '<div class="alert alert-info mt-3">🔄 Buscando...</div>';
    
    var fd = new FormData();
    fd.append('telefone', tel);
    
    fetch('/buscar-pedidos/', {
      method: 'POST',
      body: fd,
      headers: {'X-CSRFToken': getCookie('csrftoken')}
    })
    .then(function(r) { return r.json(); })
    .then(exibirResultados)
    .catch(function() {
      resultDiv.innerHTML = '<div class="alert alert-danger mt-3">❌ Erro</div>';
    });
  };

  document.getElementById('inputCpf').oninput = function(e) {
    var v = e.target.value.replace(/\D/g, '');
    v = v.replace(/(\d{3})(\d)/, '$1.$2');
    v = v.replace(/(\d{3})(\d)/, '$1.$2');
    v = v.replace(/(\d{3})(\d{1,2})$/, '$1-$2');
    e.target.value = v;
  };

  document.getElementById('inputTelefone').oninput = function(e) {
    var v = e.target.value.replace(/\D/g, '');
    v = v.replace(/(\d{2})(\d)/, '($1) $2');
    v = v.replace(/(\d{4,5})(\d{4})$/, '$1-$2');
    e.target.value = v;
  };
})();