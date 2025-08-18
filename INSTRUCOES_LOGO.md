# 🖼️ Como Substituir a Logo

## Passos para colocar sua imagem da logo:

1. **Localize o arquivo**: `rifa/static/img/pantanal-logo.png`

2. **Substitua pela sua imagem**:
   - Delete o arquivo atual `pantanal-logo.png`
   - Copie sua imagem da logo "Pantanal da Sorte" para essa pasta
   - Renomeie sua imagem para `pantanal-logo.png`

3. **Formatos recomendados**:
   - ✅ PNG (com fundo transparente) - **RECOMENDADO**
   - ✅ SVG (vetorial, melhor qualidade)
   - ✅ JPG (se tiver fundo sólido)

4. **Dimensões ideais**:
   - **Altura**: 45px (desktop) / 35px (mobile)
   - **Largura**: máximo 250px
   - **Proporção**: mantenha a proporção original

5. **Alternativa usando SVG** (melhor qualidade):
   - Se sua logo for SVG, renomeie para `pantanal-logo.svg`
   - Depois altere no arquivo `base.html` a linha:
   ```html
   <img src="{% static 'img/pantanal-logo.png' %}" alt="Pantanal da Sorte" class="logo-image">
   ```
   Para:
   ```html
   <img src="{% static 'img/pantanal-logo.svg' %}" alt="Pantanal da Sorte" class="logo-image">
   ```

## ✨ Efeitos já configurados:
- Hover com brilho verde
- Sombra suave
- Responsivo para mobile
- Transições suaves

Após substituir a imagem, recarregue a página para ver sua logo!
