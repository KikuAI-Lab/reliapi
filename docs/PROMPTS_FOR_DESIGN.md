# Промпты для дизайна ReliAPI

## Промпт 1: Минималистичная аватарка/логотип

### Описание задачи
Создать минималистичный логотип для ReliAPI в виде круглой аватарки на черном фоне. Логотип должен метафорически передавать суть продукта: reliability layer, который превращает хаос нестабильных API вызовов в стабильные и надежные запросы.

### Промпт для генерации

```
Create a minimalistic logo icon for a reliability layer API service called "ReliAPI". 

Design requirements:
- Circular icon/avatar format
- Black background (#000000 or pure black)
- Single, clear symbol that works as a metaphor
- Minimalist style, clean lines
- High contrast for visibility
- Professional and modern aesthetic

Concept: ReliAPI transforms chaotic, unreliable API calls into stable, reliable requests. It acts as a protective shield/stability engine between clients and upstream APIs.

Visual metaphor options (choose one or combine):
1. A shield with a checkmark or stability symbol inside
2. A circular arrow/loop showing transformation from chaos to order
3. A protective barrier/filter with clean output on one side
4. A stability anchor or foundation symbol
5. A circuit/connection symbol with protective elements
6. A gear or engine symbol representing the "stability engine"
7. Two overlapping circles showing connection/protection
8. A simplified lock or security symbol representing reliability

Style:
- Line art or geometric shapes
- 2-3 colors maximum (accent color: purple/violet #a89cc4 or similar)
- No gradients, flat design
- Icon should be recognizable at small sizes (64x64px minimum)
- Symmetrical or balanced composition
- Modern, tech-forward appearance

Technical:
- SVG or high-resolution PNG
- Transparent or black background
- Icon centered in circle
- Padding around icon (20% margin)
- Works on dark backgrounds

Avoid:
- Complex details
- Text/letters
- Cluttered elements
- Overly literal representations
- Bright colors that clash with black background
```

### Альтернативный промпт (более конкретный)

```
Minimalist circular logo icon: A protective shield with a stability arrow inside, on pure black background. 
The shield represents protection/reliability, the arrow represents transformation from chaos to stability. 
Style: Clean line art, single accent color (purple #a89cc4), geometric shapes, modern tech aesthetic. 
Format: Circular, centered, high contrast, works at 64x64px. 
No text, no gradients, flat design.
```

### Рекомендуемые варианты символов

1. **Щит с волной стабильности** - защита + стабильность
2. **Двойной круг с точкой** - защитный барьер вокруг стабильного ядра
3. **Стрелка в круге** - преобразование/трансформация
4. **Шестеренка с щитом** - механизм надежности
5. **Фильтр/воронка** - очистка хаоса в порядок

---

## Промпт 2: Демо-страница с анимациями

### Описание задачи
Создать красивую демонстрационную страницу для ReliAPI с дорогими, плавными анимациями, которая визуально объясняет суть работы продукта, предоставляет необходимые ссылки и показывает статистику/метрики.

### Промпт для генерации

```
Create a premium, animated demo landing page for "ReliAPI" - a reliability layer for HTTP and LLM APIs.

Page Structure:
1. Hero Section
   - Large animated title "ReliAPI"
   - Subtitle: "Stability Engine for HTTP and LLM APIs"
   - Smooth scroll indicator animation
   - Call-to-action buttons (Try on RapidAPI, Documentation, GitHub)

2. Core Concept Visualization
   - Animated diagram showing: Chaos → ReliAPI Engine → Stability
   - Left side: Chaotic, jittery API calls (red, animated squares with random movement)
   - Center: ReliAPI engine (purple/violet glowing box with pulsing animation)
   - Right side: Clean, stable output (green, aligned squares appearing smoothly)
   - Flow arrows between sections with particle effects
   - Interactive: Hover to see transformation animation

3. Interactive Features Demo
   - Toggle buttons for different reliability scenarios:
     * Provider Errors (shows automatic fallback)
     * Rate Limits (shows retry with backoff)
     * Request Storm (shows request coalescing)
     * Budget Cap Hit (shows cost throttling)
   - Each toggle triggers smooth, premium animation
   - Visual feedback showing ReliAPI handling the scenario
   - Response envelope animation appearing with success state

4. Statistics & Metrics Section
   - Animated bar charts showing:
     * Error Rate: Direct API (20%) vs With ReliAPI (1%)
     * Cost Predictability: Direct API (±30%) vs With ReliAPI (±2%)
     * P95 Latency comparison: LiteLLM (850ms), Portkey (780ms), Helicone (720ms), ReliAPI (450ms)
     * Cache Hit Rate: Direct API (15%) vs With ReliAPI (68%)
   - Charts animate on scroll into view
   - Smooth number counting animations
   - Color-coded bars (red for worse, green for better)

5. Comparison Table
   - Animated table comparing ReliAPI vs LiteLLM, Portkey, Helicone
   - Features: Self-hosted, HTTP+LLM, Idempotency, Budget caps, Minimal config, Streaming
   - Green/yellow/red status indicators with smooth transitions
   - Hover effects on rows

6. Code Examples Section
   - Animated code blocks showing:
     * Python example
     * JavaScript example
     * cURL example
   - Syntax highlighting
   - Copy-to-clipboard button with animation
   - Smooth reveal animations

7. Links & Resources Section
   - Prominent buttons/links:
     * "Try on RapidAPI" (primary CTA)
     * "Official API Endpoint"
     * "GitHub Repository"
     * "Documentation"
     * "KikuAI Lab"
   - Hover effects with smooth transitions
   - Icon animations

Design Requirements:
- Dark theme: Background #17191d, Cards #282f33
- Accent color: Purple/Violet #a89cc4
- Primary text: #e5e5e5
- Secondary text: #9ba0a5
- Success: #4ade80 (green)
- Warning: #fbbf24 (yellow)
- Error: #f87171 (red)

Animation Style:
- Smooth, premium transitions (ease-in-out, cubic-bezier)
- Particle effects for important actions
- Glow effects on interactive elements
- Smooth scroll animations (fade in, slide up)
- Parallax effects on hero section
- Micro-interactions on hover/click
- Loading states with smooth transitions
- Number counting animations
- Chart bar animations (grow from bottom)
- Icon animations (rotate, pulse, scale)

Technical Requirements:
- Responsive design (mobile, tablet, desktop)
- Smooth 60fps animations
- CSS animations preferred (no heavy JS)
- Lazy loading for performance
- Accessibility: ARIA labels, keyboard navigation
- SEO-friendly structure

Inspiration: Take visual style and animation approach from modern SaaS landing pages, but adapt the content to show ReliAPI's unique value proposition: transforming chaotic API calls into stable, reliable requests.

Specific Animations to Include:
1. Hero title: Fade in + slide up with glow effect
2. Chaos squares: Random jitter animation, red glow
3. ReliAPI engine: Pulsing glow, rotating border, particle ripples
4. Stability squares: Smooth appear animation, green glow
5. Flow arrows: Animated particles flowing
6. Toggle buttons: Smooth state transitions with glow
7. Charts: Bars grow from 0% with number counting
8. Comparison table: Row highlight on hover, smooth status transitions
9. Code blocks: Typewriter effect or fade in
10. Links: Hover scale + glow effect

Call-to-Actions:
- Primary: "Try on RapidAPI" (large, prominent, purple)
- Secondary: "View Documentation", "GitHub", etc.
- All CTAs should have hover animations and clear visual hierarchy
```

### Альтернативный промпт (более структурированный)

```
Create a premium animated landing page for ReliAPI with the following sections:

SECTION 1: HERO
- Animated title "ReliAPI" with gradient text effect
- Subtitle with fade-in animation
- Two CTA buttons: "Try on RapidAPI" (primary, purple) and "View Docs" (secondary)
- Animated scroll indicator (bouncing arrow)
- Dark background with subtle particle effects

SECTION 2: CHAOS → STABILITY VISUALIZATION
Animate this transformation:
- Left: 9 chaotic red squares (random jitter, pulsing red glow)
- Center: Purple ReliAPI engine box (pulsing glow, rotating border, particle ripples)
- Right: 9 stable green squares (smooth appear animation, green glow)
- Flow arrows with animated particles between sections
- Interactive: Click engine to see transformation animation

SECTION 3: INTERACTIVE FEATURES
4 toggle buttons in grid:
1. "Provider Errors" - Shows: API Error → ReliAPI routes to Backup → Success
2. "Rate Limits" - Shows: 429 Error → ReliAPI backs off & retries → Success  
3. "Request Storm" - Shows: Multiple requests → ReliAPI coalesces → Single response
4. "Budget Cap" - Shows: Budget bar filling → ReliAPI trims tokens → Stays within limit

Each toggle triggers smooth animation showing the scenario being handled.

SECTION 4: STATISTICS (Animated Charts)
4 chart cards, each with animated bar chart:
1. Error Rate: Direct API (20% red bar) vs ReliAPI (1% green bar)
2. Cost Predictability: Direct API (±30% yellow bar) vs ReliAPI (±2% green bar)
3. P95 Latency: LiteLLM (850ms), Portkey (780ms), Helicone (720ms), ReliAPI (450ms green)
4. Cache Hit Rate: Direct API (15% red) vs ReliAPI (68% green)

Charts animate on scroll: bars grow from 0%, numbers count up.

SECTION 5: COMPARISON TABLE
Animated table comparing ReliAPI vs competitors:
- Features: Self-hosted, HTTP+LLM, Idempotency, Budget caps, Minimal config, Streaming
- Status indicators: Green circle (✅), Yellow circle (⚠️), Red circle (❌)
- Smooth row hover effects
- Status transitions animate

SECTION 6: CODE EXAMPLES
3 code cards with syntax highlighting:
- Python example (fade in)
- JavaScript example (fade in)
- cURL example (fade in)
- Copy button with animation on each

SECTION 7: LINKS & FOOTER
- "Try on RapidAPI" button (large, purple, prominent)
- "Official API Endpoint" link
- GitHub, Documentation, KikuAI Lab links
- Footer with copyright

DESIGN SYSTEM:
Colors: #17191d (bg), #282f33 (cards), #a89cc4 (accent), #e5e5e5 (text), #4ade80 (success), #f87171 (error)
Typography: Modern sans-serif, large headings, readable body text
Spacing: Generous padding, clear sections
Animations: Smooth 60fps, ease-in-out, 300-500ms duration
Responsive: Mobile-first, breakpoints at 768px and 1024px

ANIMATION DETAILS:
- All animations should be smooth and premium-feeling
- Use CSS transforms and opacity for performance
- Stagger animations for lists/grids
- Parallax on scroll for depth
- Glow effects on interactive elements
- Particle effects for important actions
- Number counting for statistics
- Chart bars grow from bottom
- Status indicators pulse on change
```

### Ключевые элементы для анимаций (из index.html)

Из существующего `index.html` можно взять:

1. **Chaos Grid Animation** - jittery squares с random movement
2. **ReliAPI Engine** - pulsing glow, rotating border, particle ripples
3. **Stability Grid** - smooth appear animation
4. **Flow Arrows** - animated particles
5. **Toggle Buttons** - state transitions
6. **Chart Animations** - bars growing from bottom
7. **Comparison Table** - status markers with transitions

### Дополнительные рекомендации

**Для логотипа:**
- Протестировать на разных размерах (16x16, 32x32, 64x64, 128x128)
- Убедиться, что работает на темном и светлом фоне
- Проверить читаемость в маленьком размере

**Для демо-страницы:**
- Добавить loading states
- Оптимизировать для производительности (lazy loading, will-change)
- Добавить fallback для старых браузеров
- Включить analytics для отслеживания взаимодействий
- Добавить мета-теги для SEO

---

## Использование промптов

### Для логотипа:
1. Используйте промпт 1 в Midjourney, DALL-E, Stable Diffusion или другом генераторе
2. Экспериментируйте с разными вариантами метафор
3. Выберите лучший вариант и доработайте в Figma/Illustrator

### Для демо-страницы:
1. Используйте промпт 2 для генерации HTML/CSS/JS
2. Адаптируйте под существующий дизайн из `index.html`
3. Интегрируйте с реальными метриками и ссылками
4. Протестируйте производительность и анимации

---

**Примечание:** Оба промпта можно использовать с различными AI-инструментами для генерации дизайна (Midjourney, DALL-E, ChatGPT для кода, Claude для структуры и т.д.)

