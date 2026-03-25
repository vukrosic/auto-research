"""Visualize all activation functions being tested in Phase 2 experiments."""
import numpy as np
import matplotlib.pyplot as plt
import matplotlib
matplotlib.use('Agg')

x = np.linspace(-3, 3, 1000)

def relu(x): return np.maximum(x, 0)
def leaky(x, a=0.5): return np.where(x > 0, x, a * x)
def selu(x, alpha=1.6732632423543772, lam=1.0507009873554805):
    return lam * np.where(x > 0, x, alpha * (np.exp(x) - 1))
def elu(x, alpha=1.0): return np.where(x > 0, x, alpha * (np.exp(x) - 1))
def elu03(x): return elu(x, 0.3)
def gelu(x): return 0.5 * x * (1 + np.tanh(np.sqrt(2/np.pi) * (x + 0.044715 * x**3)))
def mish(x): return x * np.tanh(np.log1p(np.exp(x)))
def softplus(x, beta=1.0): return np.log1p(np.exp(beta * x)) / beta
def softsign(x): return x / (1 + np.abs(x))
def celu(x, alpha=0.5): return np.where(x > 0, x, alpha * (np.exp(x/alpha) - 1))

# ============================================================
# Figure 1: All base activations (before squaring)
# ============================================================
fig, axes = plt.subplots(2, 3, figsize=(18, 11))
fig.suptitle('Phase 2 Activation Functions — Base Functions (before squaring)', fontsize=16, fontweight='bold')

# Panel 1: H3 — Negative-side comparison (leaky variants + relu)
ax = axes[0, 0]
ax.set_title('H3: Negative-Side Information\n(more negative signal → right)', fontsize=11)
ax.plot(x, relu(x), 'k-', lw=2, label='relu (kills negatives)')
ax.plot(x, leaky(x, 0.1), '-', color='#2196F3', lw=1.5, label='leaky(0.1)')
ax.plot(x, leaky(x, 0.2), '-', color='#1976D2', lw=1.5, label='leaky(0.2)')
ax.plot(x, leaky(x, 0.5), '-', color='#E91E63', lw=2.5, label='leaky(0.5) ★ best')
ax.plot(x, leaky(x, 0.8), '-', color='#9C27B0', lw=1.5, label='leaky(0.8)')
ax.plot(x, x, '--', color='gray', lw=0.8, alpha=0.5, label='identity')
ax.axhline(0, color='gray', lw=0.5); ax.axvline(0, color='gray', lw=0.5)
ax.set_xlim(-3, 3); ax.set_ylim(-2, 3)
ax.legend(fontsize=8, loc='upper left')
ax.set_xlabel('x'); ax.set_ylabel('f(x)')

# Panel 2: H3 — Non-linear negative-side functions
ax = axes[0, 1]
ax.set_title('H3: Non-Linear Negative Shapes', fontsize=11)
ax.plot(x, relu(x), 'k-', lw=2, label='relu')
ax.plot(x, selu(x), '-', color='#FF5722', lw=2, label='selu')
ax.plot(x, elu(x), '-', color='#4CAF50', lw=2, label='elu(1.0)')
ax.plot(x, elu03(x), '--', color='#4CAF50', lw=1.5, label='elu(0.3)')
ax.plot(x, gelu(x), '-', color='#2196F3', lw=2, label='gelu')
ax.plot(x, mish(x), '-', color='#9C27B0', lw=2, label='mish')
ax.plot(x, celu(x), '-', color='#FF9800', lw=1.5, label='celu(0.5)')
ax.axhline(0, color='gray', lw=0.5); ax.axvline(0, color='gray', lw=0.5)
ax.set_xlim(-3, 3); ax.set_ylim(-2, 3)
ax.legend(fontsize=8, loc='upper left')
ax.set_xlabel('x'); ax.set_ylabel('f(x)')

# Panel 3: H2 — Signal compression functions
ax = axes[0, 2]
ax.set_title('H2: Signal Compression\n(bounded outputs)', fontsize=11)
ax.plot(x, np.tanh(x), '-', color='#E91E63', lw=2, label='tanh → [−1,1]')
ax.plot(x, 2*np.tanh(x), '--', color='#E91E63', lw=1.5, label='2·tanh → [−2,2]')
ax.plot(x, np.clip(x, -1, 1), '-', color='#F44336', lw=2, label='hardtanh → [−1,1]')
ax.plot(x, softsign(x), '-', color='#FF9800', lw=2, label='softsign → (−1,1)')
ax.plot(x, 1/(1+np.exp(-x)), '-', color='#9C27B0', lw=2, label='sigmoid → (0,1)')
ax.plot(x, np.arctan(x), '-', color='#2196F3', lw=2, label='arctan → (−π/2,π/2)')
from scipy.special import erf as scipy_erf
ax.plot(x, scipy_erf(x), '-', color='#4CAF50', lw=2, label='erf → (−1,1)')
ax.axhline(0, color='gray', lw=0.5); ax.axvline(0, color='gray', lw=0.5)
ax.set_xlim(-3, 3); ax.set_ylim(-2, 2.5)
ax.legend(fontsize=7, loc='upper left')
ax.set_xlabel('x'); ax.set_ylabel('f(x)')

# Panel 4: H3 — Sign-preserving squared activations
ax = axes[1, 0]
ax.set_title('H3: Squared Activations (sign-preserving)', fontsize=11)
y_relu2 = relu(x)**2
y_leaky2 = leaky(x, 0.5)**2
y_xabsx = x * np.abs(x)  # sign(x)*x²
y_bipolar = relu(x)**2 - 0.25*relu(-x)**2
y_linneg = np.where(x > 0, relu(x)**2, -0.5*np.abs(x))
ax.plot(x, y_relu2, 'k-', lw=2, label='relu² (baseline)')
ax.plot(x, y_leaky2, '-', color='#E91E63', lw=2.5, label='leaky(0.5)² ★')
ax.plot(x, y_xabsx, '-', color='#4CAF50', lw=2, label='x·|x| (sign-preserving)')
ax.plot(x, y_bipolar, '-', color='#9C27B0', lw=1.5, label='bipolar_relu²')
ax.plot(x, y_linneg, '--', color='#FF9800', lw=1.5, label='relu²_linneg0.5')
ax.axhline(0, color='gray', lw=0.5); ax.axvline(0, color='gray', lw=0.5)
ax.set_xlim(-3, 3); ax.set_ylim(-3, 9)
ax.legend(fontsize=8, loc='upper left')
ax.set_xlabel('x'); ax.set_ylabel('f(x)²')

# Panel 5: H2 — Squared compressed activations
ax = axes[1, 1]
ax.set_title('H2: Squared After Compression', fontsize=11)
ax.plot(x, relu(x)**2, 'k-', lw=2, label='relu² (unbounded)')
ax.plot(x, np.tanh(x)**2, '-', color='#E91E63', lw=2, label='tanh² → [0,1]')
ax.plot(x, (2*np.tanh(x))**2, '--', color='#E91E63', lw=1.5, label='(2·tanh)² → [0,4]')
ax.plot(x, np.clip(x,-1,1)**2, '-', color='#F44336', lw=2, label='hardtanh² → [0,1]')
ax.plot(x, softsign(x)**2, '-', color='#FF9800', lw=2, label='softsign² → [0,1)')
ax.plot(x, np.arctan(x)**2, '-', color='#2196F3', lw=2, label='arctan² → [0,2.47)')
ax.plot(x, np.log1p(relu(x)**2), '-', color='#795548', lw=2, label='log(1+relu²) unbounded')
y_clamp4 = np.minimum(relu(x)**2, 4)
ax.plot(x, y_clamp4, '--', color='#607D8B', lw=1.5, label='relu²_clamped4')
ax.axhline(0, color='gray', lw=0.5); ax.axvline(0, color='gray', lw=0.5)
ax.set_xlim(-3, 3); ax.set_ylim(-0.5, 9)
ax.legend(fontsize=7, loc='upper left')
ax.set_xlabel('x'); ax.set_ylabel('f(x)²')

# Panel 6: Cross-hypothesis — special shapes
ax = axes[1, 2]
ax.set_title('Cross-Hypothesis: Special Shapes', fontsize=11)
ax.plot(x, relu(x)**2, 'k-', lw=2, label='relu²')
ax.plot(x, selu(x)**2, '-', color='#FF5722', lw=2, label='selu² (H1+H2+H3)')
ax.plot(x, x * (x / (1+np.exp(-x))), '-', color='#2196F3', lw=2, label='x·silu (self-gated x²)')
ax.plot(x, x * np.tanh(x), '-', color='#4CAF50', lw=2, label='x·tanh (bounded growth)')
ax.plot(x, relu(x)**1.8, '--', color='#9E9E9E', lw=1.5, label='relu^1.8')
ax.plot(x, relu(x)**2.2, '--', color='#607D8B', lw=1.5, label='relu^2.2')
ax.plot(x, softplus(x, beta=5)**2, '-', color='#9C27B0', lw=1.5, label='softplus²(β=5)')
ax.plot(x, softplus(x, beta=0.5)**2, '--', color='#9C27B0', lw=1.5, label='softplus²(β=0.5)')
y_shifted = np.maximum(x + 0.5, 0)**2
ax.plot(x, y_shifted, ':', color='#FF9800', lw=1.5, label='shifted_relu²')
ax.axhline(0, color='gray', lw=0.5); ax.axvline(0, color='gray', lw=0.5)
ax.set_xlim(-3, 3); ax.set_ylim(-1, 9)
ax.legend(fontsize=7, loc='upper left')
ax.set_xlabel('x'); ax.set_ylabel('f(x)')

plt.tight_layout()
plt.savefig('lab/activation_functions_phase2.png', dpi=150, bbox_inches='tight')
print("Saved lab/activation_functions_phase2.png")

# ============================================================
# Figure 2: Gradient profiles (the key H1 insight)
# ============================================================
fig2, axes2 = plt.subplots(1, 2, figsize=(14, 5))
fig2.suptitle('H1: Gradient Scaling — Why It Matters', fontsize=14, fontweight='bold')

xp = np.linspace(0.01, 3, 500)  # positive side only for gradients

ax = axes2[0]
ax.set_title('Gradient magnitude for relu² variants')
ax.plot(xp, 2*xp, 'k-', lw=2, label='relu² natural (2x)')
ax.plot(xp, 1.5*xp, '-', color='#4CAF50', lw=1.5, label='grad1.5x')
ax.plot(xp, 3*xp, '-', color='#FF9800', lw=1.5, label='grad3x')
ax.plot(xp, np.sqrt(2*xp), '-', color='#2196F3', lw=1.5, label='gradsqrt')
ax.plot(xp, xp**2, '-', color='#F44336', lw=1.5, label='gradx² (explodes)')
ax.plot(xp, np.maximum(np.floor(2*xp), 0.5), '-', color='#E91E63', lw=2.5, label='gradfloor ★ best')
ax.plot(xp, np.minimum(np.ceil(2*xp), 4), '-', color='#9C27B0', lw=1.5, label='gradceil')
ax.plot(xp, np.ones_like(xp), '--', color='gray', lw=2, label='const-grad (worst)')
ax.set_xlabel('activation magnitude x'); ax.set_ylabel('gradient magnitude')
ax.set_xlim(0, 3); ax.set_ylim(0, 8)
ax.legend(fontsize=8)

ax = axes2[1]
ax.set_title('H1 Results: Post-Quant BPB (500 steps)')
names = ['gradfloor★', 'grad1.5x', 'grad3x', 'relu²\nbaseline', 'gradceil', 'gradsqrt', 'leaky05\nconstgrad', 'abs2\nconstgrad', 'gradx²']
vals = [1.4746, 1.4810, 1.4817, 1.4838, 1.4844, 1.5036, 1.5895, 1.5957, 1.7034]
colors = ['#E91E63', '#4CAF50', '#FF9800', 'black', '#9C27B0', '#2196F3', 'gray', 'gray', '#F44336']
bars = ax.barh(range(len(names)), vals, color=colors, alpha=0.8)
ax.set_yticks(range(len(names)))
ax.set_yticklabels(names, fontsize=9)
ax.set_xlabel('Post-Quant val_bpb (lower is better)')
ax.set_xlim(1.45, 1.72)
ax.axvline(1.4838, color='black', ls='--', lw=1, alpha=0.5, label='relu² baseline')
for i, v in enumerate(vals):
    ax.text(v + 0.002, i, f'{v:.4f}', va='center', fontsize=8)
ax.invert_yaxis()
ax.legend(fontsize=8)

plt.tight_layout()
plt.savefig('lab/gradient_scaling_h1.png', dpi=150, bbox_inches='tight')
print("Saved lab/gradient_scaling_h1.png")
