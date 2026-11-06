"""
Generates Figure 2.X: Real (n) and imaginary (k) parts of the complex
refractive index near a single absorption band, using the classical
Lorentz damped-oscillator model.

This is a conceptual illustration, not measured data for a specific
mineral. n and k are both derived from one complex function (see below),
so the two curves are automatically consistent with the Kramers-Kronig
relations -- this consistency is not imposed separately, it falls out
of the model.

THE MODEL:
A single damped oscillator gives a complex response of the form
    response(omega) ~ 1 / (omega_0^2 - omega^2 - i*gamma*omega)
Its real part produces the anomalous-dispersion shape of n (rising just
below resonance, dipping just above it); its imaginary part produces the
Lorentzian absorption peak of k, centered at the resonance frequency
omega_0. gamma controls the width of the band.

USAGE:
    python3 generate_anomalous_dispersion_figure.py

Produces: anomalous_dispersion.png
"""

import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

# Resonance frequency and damping (arbitrary units for this illustration;
# for a mineral-specific version, set omega_0 to that mineral's real
# ATR band position in cm-1).
omega_0 = 10.0
gamma = 0.5

omega = np.linspace(8, 12, 500)

# Imaginary part (k) -- Lorentzian absorption band, scaled to peak at 2
# for readability alongside n.
k = (gamma * omega) / ((omega_0**2 - omega**2)**2 + (gamma * omega)**2)
k = k / np.max(k) * 2

# Real part (n) -- anomalous dispersion around the same resonance.
n_background = 1.5
n_offset = (omega_0**2 - omega**2) / ((omega_0**2 - omega**2)**2 + (gamma * omega)**2)
n = n_background + n_offset * 1.5

plt.figure(figsize=(7, 4))
plt.plot(omega, n, label='Real part (n) - Anomalous Dispersion', color='blue', linewidth=2)
plt.plot(omega, k, label='Imaginary part (k) - Absorption Band', color='red', linestyle='--', linewidth=2)
plt.axvline(omega_0, color='gray', linestyle=':', alpha=0.7)

# Label placed in open space near the bottom of the plot, not on the
# legend; $...$ used (not \(...\)) so nu_0 renders as math text rather
# than literal backslash characters.
plt.text(omega_0 + 0.1, 0.15, 'Resonance Frequency ($\\nu_0$)', fontsize=9, color='gray')

plt.title('Complex Refractive Index Across an Absorption Band')
plt.xlabel('Frequency / Wavenumber (arbitrary units)')
plt.ylabel('Optical Constants (n, k)')
plt.legend(loc='upper right')
plt.grid(True, linestyle=':', alpha=0.6)
plt.tight_layout()
plt.savefig('anomalous_dispersion.png', dpi=300)
print("Saved anomalous_dispersion.png")
