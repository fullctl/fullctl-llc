function getSystemTheme() {
    return window.matchMedia('(prefers-color-scheme: dark)').matches ? 'dark' : 'light';
}

matchMedia('(prefers-color-scheme: dark)').onchange = (e) => {
  let systemTheme = getSystemTheme();
  // Update the theme, as long as there's no theme override
  if (localStorage.getItem('theme') === null) {
    setTheme(systemTheme)
  }
}

function toggleTheme() {
    if (detectTheme() === 'dark')
        setTheme('light');
    else
        setTheme('dark');
}

function setTheme(newTheme) {
  document.documentElement.setAttribute('data-theme', newTheme)
  if (newTheme === getSystemTheme()) {
    // Remove override if the user sets the theme to match the system theme
    localStorage.removeItem('theme')
  } else {
    localStorage.setItem('theme', newTheme)
  }
}

function detectTheme() {
    var themeOverride = localStorage.getItem('theme')
    if (themeOverride == 'dark' || themeOverride === 'light') {
        // Override the system theme
        return themeOverride
    } 
    // Use system theme
    return getSystemTheme();
}

document.addEventListener("DOMContentLoaded", () => {
    document.documentElement.setAttribute('data-theme', detectTheme())

    $(".theme-switcher").click(() => {
        toggleTheme();
    });
});
