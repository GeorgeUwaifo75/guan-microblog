/*
 * GuAn i18n - lightweight runtime translation (English <-> Spanish).
 *
 * How it works
 *  - English is the source language. Templates and JS keep their English text.
 *  - When the active language is "es", every text node / placeholder / title /
 *    aria-label / alt in the page is looked up in DICT (exact match) or run
 *    through PATTERNS (dynamic strings such as "5 characters remaining").
 *  - A MutationObserver translates content that the app renders later
 *    (innerHTML templates, textContent updates, modals, notifications...).
 *  - alert(), confirm() and prompt() messages are translated as well, which
 *    also covers server error messages (HTTPException details).
 *  - User-generated content (posts, names, bios, hashtags) is never translated.
 *
 * Active language is resolved from:
 *    window.GUAN_LANG (set by the server for logged-in pages)
 *    -> localStorage "guan_lang" (login/signup page)
 *    -> "en"
 *
 * Add a string: put the exact English text as the key in DICT (or add a
 * regex to PATTERNS for text containing variables).
 */
(function () {
  'use strict';

  var STORAGE_KEY = 'guan_lang';
  var SUPPORTED = { en: true, es: true };

  // ------------------------------------------------------------------
  // Exact-match dictionary (key = English text with whitespace collapsed)
  // ------------------------------------------------------------------
  var DICT = {
    // ---- Landing page / login / signup / forgot password ----
    'GuAn - Freedom of Expression': 'GuAn - Libertad de expresión',
    'Dashboard - GuAn': 'Panel - GuAn',
    '© 2026 GuAn Microblogging Platform. All rights reserved.': '© 2026 GuAn Plataforma de Microblogging. Todos los derechos reservados.',
    "Freedom of expression is right but don't hurt others with yours.": 'La libertad de expresión es un derecho, pero no hieras a los demás con la tuya.',
    "Freedom of expression is a right but don't hurt others with it!": '¡La libertad de expresión es un derecho, pero no hieras a los demás con ella!',
    '🐏 Welcome to GuAn': '🐏 Bienvenido a GuAn',
    'Express yourself freely, but responsibly.': 'Exprésate libremente, pero con responsabilidad.',
    'Get Started →': 'Comenzar →',
    'Sign Up': 'Regístrate',
    'Login': 'Iniciar sesión',
    'Logout': 'Cerrar sesión',
    'Dashboard': 'Panel',
    'Talos': 'Talos',
    'Share Talo': 'Compartir Talo',
    'Re-Talo': 'Re-Talo',
    'Reply-Talo': 'Responder Talo',
    'Diamond Likes': 'Likes de diamante',
    'Premium Priority': 'Prioridad Premium',
    'Share your thoughts in 250 characters or less.': 'Comparte tus ideas en 250 caracteres o menos.',
    'Short posts up to 250 chars with up to 4 photos': 'Publicaciones cortas de hasta 250 caracteres con hasta 4 fotos',
    "Share and quote others' talos": 'Comparte y cita los talos de otros',
    "You can reply to post' talos": 'Puedes responder a los talos de las publicaciones',
    'You can share on other platforms': 'Puedes compartir en otras plataformas',
    'Show appreciation with diamond-shaped likes': 'Muestra tu aprecio con likes en forma de diamante',
    '70% higher visibility for premium users': '70% más de visibilidad para usuarios premium',
    'Login to GuAn': 'Inicia sesión en GuAn',
    'User ID': 'ID de usuario',
    'Password': 'Contraseña',
    'Show password': 'Mostrar contraseña',
    'Hide password': 'Ocultar contraseña',
    'Forgot password?': '¿Olvidaste tu contraseña?',
    'Create GuAn Account': 'Crear cuenta de GuAn',
    'Email *': 'Correo electrónico *',
    'Email': 'Correo electrónico',
    'User ID * (no spaces)': 'ID de usuario * (sin espacios)',
    'User ID cannot contain spaces': 'El ID de usuario no puede contener espacios',
    'First Name *': 'Nombre *',
    'Last Name *': 'Apellido *',
    'Password *': 'Contraseña *',
    'Gender *': 'Género *',
    'Male': 'Masculino',
    'Female': 'Femenino',
    'Age * (must be 18+)': 'Edad * (debes tener 18 años o más)',
    'Country *': 'País *',
    'Select your country': 'Selecciona tu país',
    'English-speaking': 'Países de habla inglesa',
    'Spanish-speaking': 'Países de habla hispana',
    'Nigeria': 'Nigeria',
    'Kenya': 'Kenia',
    'Ghana': 'Ghana',
    'United States': 'Estados Unidos',
    'United Kingdom': 'Reino Unido',
    'Canada': 'Canadá',
    'Spain': 'España',
    'Mexico': 'México',
    'Venezuela': 'Venezuela',
    'Interests (optional)': 'Intereses (opcional)',
    'Reset Your Password': 'Restablece tu contraseña',
    'Enter your User ID, email, and age on your account, then choose a new password.': 'Ingresa tu ID de usuario, correo electrónico y la edad de tu cuenta, y luego elige una nueva contraseña.',
    'Age (*stated when you registered*)': 'Edad (*la indicada al registrarte*)',
    'New Password': 'Nueva contraseña',
    'Confirm New Password': 'Confirmar nueva contraseña',
    'Reset Password': 'Restablecer contraseña',
    'Back to Login': 'Volver a iniciar sesión',
    'Please contact the administrator at': 'Comunícate con el administrador en',
    'to have your password reset.': 'para que restablezca tu contraseña.',
    'Too many unsuccessful verification attempts. For your security, self-service reset has been disabled.': 'Demasiados intentos de verificación fallidos. Por tu seguridad, el restablecimiento por cuenta propia ha sido desactivado.',

    // ---- Alerts / messages on the landing page ----
    'Login failed': 'Error al iniciar sesión',
    'Signup failed': 'Error al registrarse',
    'Password reset failed': 'Error al restablecer la contraseña',
    'Request timed out. Please check your connection and try again.': 'Se agotó el tiempo de espera. Revisa tu conexión e inténtalo de nuevo.',
    'Network error. Please check your connection and try again.': 'Error de red. Revisa tu conexión e inténtalo de nuevo.',
    'You must be 18 or older to sign up': 'Debes tener 18 años o más para registrarte',
    'You must be 18 or older': 'Debes tener 18 años o más',
    'User ID cannot be empty': 'El ID de usuario no puede estar vacío',
    'Account created successfully! Please login.': '¡Cuenta creada con éxito! Por favor, inicia sesión.',
    'New password and confirmation do not match': 'La nueva contraseña y su confirmación no coinciden',
    'Password reset successful! Please login with your new password.': '¡Contraseña restablecida con éxito! Inicia sesión con tu nueva contraseña.',
    'Password reset successful. Please log in with your new password.': 'Contraseña restablecida con éxito. Inicia sesión con tu nueva contraseña.',

    // ---- Server (HTTPException) messages ----
    'Invalid credentials': 'Credenciales no válidas',
    'Account deactivated': 'Cuenta desactivada',
    'Admin account deactivated': 'Cuenta de administrador desactivada',
    'User ID already exists': 'El ID de usuario ya existe',
    'Email already exists': 'El correo electrónico ya existe',
    'Please select a valid country from the list': 'Selecciona un país válido de la lista',
    'User ID and email are required': 'El ID de usuario y el correo electrónico son obligatorios',
    'New password must be at least 4 characters': 'La nueva contraseña debe tener al menos 4 caracteres',
    'Current password is incorrect': 'La contraseña actual es incorrecta',
    'Unknown error': 'Error desconocido',
    'API is currently slow. Please try again in a moment.': 'El servicio está lento en este momento. Inténtalo de nuevo en un instante.',

    // ---- Dashboard: header / navigation ----
    'GuAn': 'GuAn',
    'Menu': 'Menú',
    'Notifications': 'Notificaciones',
    'Mark all posts as viewed': 'Marcar todas las publicaciones como vistas',
    'Chat with Ivie AI': 'Chatea con Ivie AI',
    'Clear chat history': 'Borrar historial del chat',
    'Search posts, hashtags, or @username...': 'Buscar publicaciones, hashtags o @usuario...',
    'Loading...': 'Cargando...',
    'Clear filter': 'Quitar filtro',
    'Showing posts with tag:': 'Mostrando publicaciones con la etiqueta:',
    'Pull to refresh...': 'Desliza para actualizar...',
    'Release to refresh...': 'Suelta para actualizar...',
    'Refreshing...': 'Actualizando...',
    'Gists': 'Gists',
    'Selected interests appear as the "Gists" strip on your dashboard. Deselect all to hide it.': 'Los intereses seleccionados aparecen como la franja "Gists" en tu panel. Deselecciónalos todos para ocultarla.',

    // ---- Dashboard: profile card / sidebar ----
    'Followers': 'Seguidores',
    'Following': 'Siguiendo',
    '+ Follow': '+ Seguir',
    '✓ Following': '✓ Siguiendo',
    '✏️ Edit': '✏️ Editar',
    '· Balance:': '· Saldo:',
    'Balance:': 'Saldo:',
    'TaC': 'TaC',
    '🐏 PREMIUM': '🐏 PREMIUM',
    '⭐ Get Premium (₦7,800/yr)': '⭐ Hazte Premium (₦7,800/año)',
    '🔥 Trending Today': '🔥 Tendencias de hoy',
    'No trending topics yet': 'Aún no hay temas en tendencia',

    // ---- Dashboard: composing / posts ----
    "What's happening? (max 250 characters)": '¿Qué está pasando? (máx. 250 caracteres)',
    '250 characters remaining': '250 caracteres restantes',
    '0 files selected': '0 archivos seleccionados',
    '📷 Add Photo/Video': '📷 Añadir foto/video',
    'Talo →': 'Talo →',
    'Uploading...': 'Subiendo...',
    'Creating post...': 'Creando publicación...',
    'No talos yet. Be the first to post!': 'Aún no hay talos. ¡Sé el primero en publicar!',
    '⭐ PROMOTED': '⭐ PROMOCIONADO',
    '⭐ Promoted': '⭐ Promocionado',
    '⭐ Promote Post': '⭐ Promocionar publicación',
    '🗑️ Delete Post': '🗑️ Eliminar publicación',
    'Original post:': 'Publicación original:',
    'Randomly Featured': 'Destacado al azar',
    'End of promoted content (refresh for new random posts)': 'Fin del contenido promocionado (actualiza para ver nuevas publicaciones al azar)',
    '🎲 No promoted posts this time! Pull to refresh for a new chance (25% each).': '🎲 ¡No hay publicaciones promocionadas esta vez! Desliza para actualizar y tener otra oportunidad (25% cada vez).',
    'Your browser does not support the video tag.': 'Tu navegador no admite la etiqueta de video.',
    'ready': 'listo',
    'Full size image': 'Imagen a tamaño completo',
    'Photo': 'Foto',
    'Profile': 'Perfil',
    'Profile Photo': 'Foto de perfil',
    'No results found': 'No se encontraron resultados',

    // ---- Dashboard: modals ----
    'Edit Profile': 'Editar perfil',
    'First Name': 'Nombre',
    'Last Name': 'Apellido',
    'Bio': 'Biografía',
    'Tell us about yourself...': 'Cuéntanos sobre ti...',
    'Interests': 'Intereses',
    '📷 Change Photo': '📷 Cambiar foto',
    'Save Changes': 'Guardar cambios',
    'Cancel': 'Cancelar',
    '🔐 Change Password': '🔐 Cambiar contraseña',
    'Current Password': 'Contraseña actual',
    'Enter current password': 'Ingresa la contraseña actual',
    'Enter new password (min 6 characters)': 'Ingresa la nueva contraseña (mín. 6 caracteres)',
    'Confirm new password': 'Confirma la nueva contraseña',
    'Password must be at least 6 characters': 'La contraseña debe tener al menos 6 caracteres',
    '🔐 Password Reset Required': '🔐 Se requiere restablecer la contraseña',
    'An administrator has reset your password. For your security, please set a new password before continuing.': 'Un administrador ha restablecido tu contraseña. Por tu seguridad, establece una nueva contraseña antes de continuar.',
    'Current (Temporary) Password': 'Contraseña actual (temporal)',
    'Enter the temporary password': 'Ingresa la contraseña temporal',
    'Set New Password': 'Establecer nueva contraseña',
    'Updating...': 'Actualizando...',
    'Please fill in all fields.': 'Por favor, completa todos los campos.',
    'New password must be at least 6 characters.': 'La nueva contraseña debe tener al menos 6 caracteres.',
    'New passwords do not match.': 'Las nuevas contraseñas no coinciden.',
    'New password must be at least 6 characters': 'La nueva contraseña debe tener al menos 6 caracteres',
    'New passwords do not match': 'Las nuevas contraseñas no coinciden',
    'Please fill in all password fields to change your password': 'Completa todos los campos de contraseña para cambiarla',
    'Failed to update password. Please check the temporary password and try again.': 'No se pudo actualizar la contraseña. Revisa la contraseña temporal e inténtalo de nuevo.',
    'Your password has been updated. Please log in again with your new password.': 'Tu contraseña ha sido actualizada. Inicia sesión de nuevo con tu nueva contraseña.',
    'Select Promotion Package': 'Selecciona un paquete de promoción',
    'Boost your post visibility with our promotion packages!': '¡Aumenta la visibilidad de tu publicación con nuestros paquetes de promoción!',
    '⭐ Promote Your Post': '⭐ Promociona tu publicación',
    '📅 3 Days Promotion': '📅 Promoción de 3 días',
    '📅 7 Days Promotion': '📅 Promoción de 7 días',
    '📅 30 Days Promotion': '📅 Promoción de 30 días',
    'Get featured for 3 days': 'Destaca durante 3 días',
    'Get featured for 7 days (Best Value)': 'Destaca durante 7 días (Mejor valor)',
    'Get featured for 30 days (Premium)': 'Destaca durante 30 días (Premium)',
    'Selected Package': 'Paquete seleccionado',
    'No package selected': 'Ningún paquete seleccionado',
    'Continue to Payment →': 'Continuar al pago →',
    '🪙 Send TaC': '🪙 Enviar TaC',
    "Beneficiary's Account ID": 'ID de cuenta del beneficiario',
    'Amount (TaC)': 'Monto (TaC)',
    'Send TaC →': 'Enviar TaC →',
    'Sending...': 'Enviando...',
    'Send': 'Enviar',
    '🧠 Ivie AI': '🧠 Ivie AI',
    "👋 Hi! I'm Ivie, your AI assistant. Ask me anything.": '👋 ¡Hola! Soy Ivie, tu asistente de IA. Pregúntame lo que quieras.',
    'Type a message...': 'Escribe un mensaje...',
    'From': 'De',
    'from': 'de',
    '🔄 Reposted from': '🔄 Republicado de',
    'Reposting...': 'Republicando...',

    // ---- Dashboard: notifications ----
    'No notifications yet': 'Aún no hay notificaciones',
    'Error loading notifications': 'Error al cargar las notificaciones',
    'Error loading followers': 'Error al cargar los seguidores',
    'Error loading following list': 'Error al cargar la lista de seguidos',
    'Reposted your post': 'Republicó tu publicación',
    'Liked your post': 'Le gustó tu publicación',
    'Replied to your post': 'Respondió a tu publicación',
    'Replied to your comment': 'Respondió a tu comentario',
    'Started following you': 'Comenzó a seguirte',
    'Sent you TaC': 'Te envió TaC',
    'Mentioned you': 'Te mencionó',
    'New notification': 'Nueva notificación',
    'just now': 'ahora mismo',

    // ---- Dashboard: alerts / toasts ----
    'Maximum 4 photos per post': 'Máximo 4 fotos por publicación',
    'Please enter some content': 'Por favor, escribe algo de contenido',
    'Your post contains inappropriate language. Please review and try again.': 'Tu publicación contiene lenguaje inapropiado. Revísala e inténtalo de nuevo.',
    'Your reply contains inappropriate language. Please review and try again.': 'Tu respuesta contiene lenguaje inapropiado. Revísala e inténtalo de nuevo.',
    'Failed to create post. Please try again.': 'No se pudo crear la publicación. Inténtalo de nuevo.',
    'Error updating profile. Please try again.': 'Error al actualizar el perfil. Inténtalo de nuevo.',
    'Failed to update profile': 'No se pudo actualizar el perfil',
    'Failed to update follow status': 'No se pudo actualizar el estado de seguimiento',
    'No post selected for promotion': 'No hay ninguna publicación seleccionada para promocionar',
    'Please select a promotion package': 'Selecciona un paquete de promoción',
    'You can either upload 1 video (max 20s) OR 1-4 photos. Please select valid files.': 'Puedes subir 1 video (máx. 20 s) O de 1 a 4 fotos. Selecciona archivos válidos.',
    'Video must be 20 seconds or less.': 'El video debe durar 20 segundos o menos.',
    'Unable to read video file. Please try another.': 'No se pudo leer el archivo de video. Prueba con otro.',
    '⚠️ Are you sure you want to delete this post? This action cannot be undone.': '⚠️ ¿Seguro que quieres eliminar esta publicación? Esta acción no se puede deshacer.',
    'Copy this text to share:': 'Copia este texto para compartir:',
    '✓ Post deleted successfully': '✓ Publicación eliminada con éxito',
    'Failed to delete post': 'No se pudo eliminar la publicación',
    'Network error. Please try again.': 'Error de red. Inténtalo de nuevo.',
    'Network error': 'Error de red',
    'Could not fetch your wallet balance.': 'No se pudo obtener el saldo de tu billetera.',
    "Please enter the beneficiary's account ID.": 'Ingresa el ID de cuenta del beneficiario.',
    'Please enter a valid amount greater than zero.': 'Ingresa un monto válido mayor que cero.',
    'You cannot send more TaC than you currently have.': 'No puedes enviar más TaC de los que tienes.',
    '✓ Post reposted successfully!': '✓ ¡Publicación republicada con éxito!',
    'Failed to repost': 'No se pudo republicar',
    '✓ Post created successfully!': '✓ ¡Publicación creada con éxito!',
    '✓ Post created! The 30,000 TaC supply cap has been reached, so no TaC was earned this time.': '✓ ¡Publicación creada! Se alcanzó el límite de 30,000 TaC en circulación, así que esta vez no se ganaron TaC.',
    '✓ All posts marked as viewed': '✓ Todas las publicaciones marcadas como vistas',
    '✓ Payment successful! Your post is now promoted.': '✓ ¡Pago exitoso! Tu publicación ya está promocionada.',
    'Payment received! Admin will verify your promotion.': '¡Pago recibido! El administrador verificará tu promoción.',
    'Payment cancelled': 'Pago cancelado',
    'Failed to initiate promotion': 'No se pudo iniciar la promoción',
    'Failed to initiate payment': 'No se pudo iniciar el pago',
    '🎉 Premium upgrade successful! You now have premium status.': '🎉 ¡Actualización a Premium exitosa! Ahora tienes estatus premium.',
    'Payment confirmed but upgrade failed. Please contact support.': 'Pago confirmado, pero la actualización falló. Comunícate con soporte.',
    'Payment received but verification failed. Please contact support.': 'Pago recibido, pero la verificación falló. Comunícate con soporte.',
    '📋 Share text copied to clipboard!': '📋 ¡Texto para compartir copiado al portapapeles!',
    'Failed to load Paystack script': 'No se pudo cargar el script de Paystack',
    'Failed to fetch': 'No se pudo conectar con el servidor'
  };

  // ------------------------------------------------------------------
  // Pattern rules for strings that contain variables
  // ------------------------------------------------------------------
  var TIME_UNITS = { s: 's', m: 'min', h: 'h', d: 'd', w: 'sem', mo: 'mes', y: 'a' };

  function trTimeAgo(str) {
    return str.replace(/(\d+)(mo|y|w|d|h|m|s)/g, function (_, n, u) {
      return n + (TIME_UNITS[u] || u);
    });
  }

  var PATTERNS = [
    // compact "time ago" labels produced by formatTimeAgo(): 5s, 3m 20s, 2h, 1w 3d, 2mo ...
    [/^\d+(?:mo|y|w|d|h|m|s)(?: \d+(?:mo|y|w|d|h|m|s))?$/, function (m) { return trTimeAgo(m[0]); }],
    [/^(\d+) characters remaining$/, function (m) { return m[1] + ' caracteres restantes'; }],
    [/^(\d+) characters over limit$/, function (m) { return m[1] + ' caracteres de más'; }],
    [/^(\d+) files? selected$/, function (m) { return m[1] + (m[1] === '1' ? ' archivo seleccionado' : ' archivos seleccionados'); }],
    [/^Content cannot exceed (\d+) characters$/, function (m) { return 'El contenido no puede superar los ' + m[1] + ' caracteres'; }],
    [/^Uploading (photo|video|image)s? (\d+)\/(\d+)\.\.\.$/, function (m) { return 'Subiendo ' + (m[1] === 'photo' ? 'foto' : m[1] === 'image' ? 'imagen' : 'video') + ' ' + m[2] + '/' + m[3] + '...'; }],
    [/^(\d+)\/(\d+) left today$/, function (m) { return m[1] + '/' + m[2] + ' restantes hoy'; }],
    [/^(\d+) days? Package$/, function (m) { return 'Paquete de ' + m[1] + (m[1] === '1' ? ' día' : ' días'); }],
    [/^(\d+) attempts? remaining before you'll need to request an admin reset\.$/, function (m) { return 'Te ' + (m[1] === '1' ? 'queda ' + m[1] + ' intento' : 'quedan ' + m[1] + ' intentos') + ' antes de tener que solicitar un restablecimiento al administrador.'; }],
    [/^Too many failed verification attempts\. Please contact the administrator at (.+) to have your password reset\.$/, function (m) { return 'Demasiados intentos de verificación fallidos. Comunícate con el administrador en ' + m[1] + ' para que restablezca tu contraseña.'; }],
    [/^Verification failed - User ID, email, and age must all match your account\. (\d+) attempt\(s\) remaining before you'll need to contact the administrator at (.+)\.$/, function (m) { return 'Falló la verificación: el ID de usuario, el correo electrónico y la edad deben coincidir con tu cuenta. Te quedan ' + m[1] + ' intento(s) antes de tener que comunicarte con el administrador en ' + m[2] + '.'; }],
    [/^✓ Post deleted · -(.+) TaC reversed$/, function (m) { return '✓ Publicación eliminada · -' + m[1] + ' TaC revertidos'; }],
    [/^🪙 Your GuAn wallet balance: (.+) TaC$/, function (m) { return '🪙 Saldo de tu billetera GuAn: ' + m[1] + ' TaC'; }],
    [/^✓ Sent (.+) TaC to @(.+)!$/, function (m) { return '✓ ¡Se enviaron ' + m[1] + ' TaC a @' + m[2] + '!'; }],
    [/^✓ Post created! \+(.+) TaC earned$/, function (m) { return '✓ ¡Publicación creada! +' + m[1] + ' TaC ganados'; }],
    [/^Sent you (.+) TaC$/, function (m) { return 'Te envió ' + m[1] + ' TaC'; }],
    [/^Failed to create post: (.+)$/, function (m) { return 'No se pudo crear la publicación: ' + tr(m[1]); }],
    [/^Error uploading photo: (.+)$/, function (m) { return 'Error al subir la foto: ' + tr(m[1]); }],
    [/^Login failed: (.+)$/, function (m) { return 'Error al iniciar sesión: ' + tr(m[1]); }],
    [/^Signup failed: (.+)$/, function (m) { return 'Error al registrarse: ' + tr(m[1]); }],
    [/^No results found for "(.+)"$/, function (m) { return 'No se encontraron resultados para "' + m[1] + '"'; }],
    [/^🔄 Reposted from (@.+)$/, function (m) { return '🔄 Republicado de ' + m[1]; }],
    [/^from (@.+)$/, function (m) { return 'de ' + m[1]; }]
  ];

  // ------------------------------------------------------------------
  // Core translate function: English string -> Spanish (or unchanged)
  // ------------------------------------------------------------------
  function tr(str) {
    if (typeof str !== 'string' || !str) return str;
    var core = str.replace(/\s+/g, ' ').trim();
    if (!core) return str;
    var hit = DICT[core];
    if (hit !== undefined) return hit;
    for (var i = 0; i < PATTERNS.length; i++) {
      var m = core.match(PATTERNS[i][0]);
      if (m) return PATTERNS[i][1](m);
    }
    // Icon/emoji prefix, e.g. "🔄 Reposted your post" (the app prepends the icon
    // to the message): translate the text and keep the prefix.
    var p = core.match(/^([^\p{L}\p{N}@"]+)(.+)$/u);
    if (p && p[2] !== core) {
      var rest = tr(p[2]);
      if (rest !== p[2]) return p[1] + rest;
    }
    return str;
  }

  // ------------------------------------------------------------------
  // State
  // ------------------------------------------------------------------
  var lang = 'en';
  var observer = null;
  var textRecords = new WeakMap();   // text node -> { en, out }
  var trackedText = [];              // translated text nodes (to restore -> English)
  var SKIP_SELECTOR = '[translate="no"], .no-i18n, .talo-content, .talo-user-name, .talo-user-id, .trending-item';
  var SKIP_TAGS = { SCRIPT: 1, STYLE: 1, TEXTAREA: 1, NOSCRIPT: 1, CODE: 1, PRE: 1 };
  var ATTRS = ['placeholder', 'title', 'aria-label', 'alt', 'label'];

  function resolveLang() {
    var l = (window.GUAN_LANG || '').toLowerCase();
    if (!SUPPORTED[l]) {
      try { l = (localStorage.getItem(STORAGE_KEY) || '').toLowerCase(); } catch (e) { l = ''; }
    }
    return SUPPORTED[l] ? l : 'en';
  }

  function skipEl(el) {
    if (!el || el.nodeType !== 1) return false;
    if (SKIP_TAGS[el.tagName]) return true;
    return !!(el.closest && el.closest(SKIP_SELECTOR));
  }

  // ---- text nodes ----
  function translateTextNode(node) {
    var parent = node.parentNode;
    if (!parent || skipEl(parent)) return;
    var cur = node.nodeValue;
    if (!cur || !/\S/.test(cur)) return;

    var rec = textRecords.get(node);
    var en = (rec && cur === rec.out) ? rec.en : cur;   // app rewrote it -> new English source
    var out = en;
    if (lang === 'es') {
      var lead = en.match(/^\s*/)[0];
      var trail = en.match(/\s*$/)[0];
      var t = tr(en);
      out = (t === en) ? en : lead + t.trim() + trail;
    }
    if (out !== cur) node.nodeValue = out;
    if (out !== en) {
      if (!rec) trackedText.push(node);
      textRecords.set(node, { en: en, out: out });
    } else if (rec) {
      textRecords.delete(node);
    }
  }

  // ---- attributes ----
  function translateAttrs(el) {
    if (el.nodeType !== 1 || skipEl(el)) return;
    var names = ATTRS.slice();
    if (el.tagName === 'INPUT' && /^(button|submit|reset)$/i.test(el.type)) names.push('value');
    for (var i = 0; i < names.length; i++) {
      var a = names[i];
      if (!el.hasAttribute(a)) continue;
      var store = 'data-i18n-en-' + a;
      var cur = el.getAttribute(a);
      var orig = el.hasAttribute(store) ? el.getAttribute(store) : null;
      // If the current value is our own translation of the stored English, the
      // English source is the stored value; otherwise the app set a new value.
      var en = (orig !== null && cur === tr(orig)) ? orig : cur;
      var out = (lang === 'es') ? tr(en) : en;
      if (out !== cur) el.setAttribute(a, out);
      if (out !== en) el.setAttribute(store, en);
      else if (el.hasAttribute(store)) el.removeAttribute(store);
    }
  }

  function walk(root) {
    if (!root) return;
    if (root.nodeType === 3) { translateTextNode(root); return; }
    if (root.nodeType !== 1 && root.nodeType !== 9 && root.nodeType !== 11) return;
    if (root.nodeType === 1 && skipEl(root)) return;
    if (root.nodeType === 1) translateAttrs(root);
    var child = root.firstChild;
    while (child) {
      if (child.nodeType === 3) translateTextNode(child);
      else if (child.nodeType === 1) walk(child);
      child = child.nextSibling;
    }
  }

  function restoreEnglish() {
    for (var i = 0; i < trackedText.length; i++) {
      var n = trackedText[i];
      var rec = textRecords.get(n);
      if (rec && n.nodeValue === rec.out) n.nodeValue = rec.en;
      textRecords.delete(n);
    }
    trackedText = [];
  }

  function startObserver() {
    if (observer || !window.MutationObserver) return;
    observer = new MutationObserver(function (mutations) {
      if (lang !== 'es') return;
      for (var i = 0; i < mutations.length; i++) {
        var m = mutations[i];
        if (m.type === 'childList') {
          for (var j = 0; j < m.addedNodes.length; j++) walk(m.addedNodes[j]);
        } else if (m.type === 'characterData') {
          translateTextNode(m.target);
        } else if (m.type === 'attributes') {
          translateAttrs(m.target);
        }
      }
    });
    observer.observe(document.documentElement, {
      childList: true, subtree: true, characterData: true,
      attributes: true, attributeFilter: ATTRS.concat(['value'])
    });
  }

  function apply() {
    if (!document.documentElement) return;
    document.documentElement.setAttribute('lang', lang);
    if (lang === 'es') {
      walk(document.documentElement);
    } else {
      restoreEnglish();
      // restore translated attributes
      var els = document.querySelectorAll('[data-i18n-en-placeholder],[data-i18n-en-title],[data-i18n-en-aria-label],[data-i18n-en-alt],[data-i18n-en-label],[data-i18n-en-value]');
      for (var i = 0; i < els.length; i++) {
        ATTRS.concat(['value']).forEach(function (a) {
          var store = 'data-i18n-en-' + a;
          if (els[i].hasAttribute(store)) {
            els[i].setAttribute(a, els[i].getAttribute(store));
            els[i].removeAttribute(store);
          }
        });
      }
    }
  }

  function setLang(next, persist) {
    next = (next || '').toLowerCase();
    if (!SUPPORTED[next]) next = 'en';
    var changed = next !== lang;
    lang = next;
    if (persist !== false) {
      try { localStorage.setItem(STORAGE_KEY, lang); } catch (e) {}
    }
    if (changed) apply();
    return lang;
  }

  // ---- translate native dialogs (covers server error messages shown via alert) ----
  var nativeAlert = window.alert ? window.alert.bind(window) : null;
  var nativeConfirm = window.confirm ? window.confirm.bind(window) : null;
  var nativePrompt = window.prompt ? window.prompt.bind(window) : null;
  if (nativeAlert) window.alert = function (msg) { return nativeAlert(lang === 'es' ? tr(String(msg)) : msg); };
  if (nativeConfirm) window.confirm = function (msg) { return nativeConfirm(lang === 'es' ? tr(String(msg)) : msg); };
  if (nativePrompt) window.prompt = function (msg, def) { return nativePrompt(lang === 'es' ? tr(String(msg)) : msg, def); };

  // ---- public API ----
  window.GuanI18n = {
    get lang() { return lang; },
    setLang: setLang,
    t: function (s) { return lang === 'es' ? tr(s) : s; },
    apply: apply
  };

  // ---- boot ----
  lang = resolveLang();
  function boot() {
    if (lang === 'es') apply();
    startObserver();
  }
  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', boot);
  } else {
    boot();
  }
  // The login page is restored from bfcache on Back; re-resolve and re-apply.
  window.addEventListener('pageshow', function (e) {
    if (e.persisted) { var l = resolveLang(); if (l !== lang) setLang(l, false); }
  });
})();
