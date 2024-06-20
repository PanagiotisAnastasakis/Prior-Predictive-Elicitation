import jax
import jax.numpy as jnp
import jax.random as jr
import jax.scipy.stats as jss
from dirichlet import dirichlet_log_likelihood, alpha_mle_


def get_gaussian_probs(partitions, lam):

    mu_1 = lam[0]
    sigma = lam[1]
    sigma_1 = lam[2]

    p1 = jss.norm.cdf(
        (partitions[:, 1] - mu_1) / jnp.sqrt(sigma**2 + sigma_1**2)
    ) - jss.norm.cdf((partitions[:, 0] - mu_1) / jnp.sqrt(sigma**2 + sigma_1**2))

    return p1


@jax.jit
def likelihood_priorpredprob_grad(alpha, probs, expert_probs):
    # If alpha is not provided, compute the MLE
    if alpha is None:

        def likelihood_fn(probs):
            alpha = alpha_mle_(probs, expert_probs)
            return dirichlet_log_likelihood(alpha, probs, expert_probs)

    else:
        likelihood_fn = lambda probs: dirichlet_log_likelihood(
            alpha, probs, expert_probs
        )

    grad_fn = jax.grad(likelihood_fn)
    likelihood_gradient = grad_fn(probs)
    return likelihood_gradient


@jax.jit
def stochastic_derivative(lambd, partition):
    a, b = partition
    pivot_sample = sampler_fn(rng_key, (num_samples,))

    def function_to_optimize(lambd, a, b):
        theta = pivot_fn(lambd, pivot_sample)
        return (cdf_fn(theta, b, lambd) - cdf_fn(theta, a, lambd)).mean()

    stochastic_gradient = jax.grad(function_to_optimize)
    return stochastic_gradient(lambd, a, b)


if __name__ == "__main__":
    partitions = jnp.array([[-1000, -2], [-2, 3], [3, 1000]])
    expert_probs = jnp.array([0.2, 0.7, 0.1])

    # Try simple Gaussian example
    alpha = 1.0
    lambd_0 = jnp.ones(3)
    rng_key = jr.key(0)
    num_samples = 10
    sampler_fn = jr.normal
    cdf_fn = lambda theta, a, lambd: jss.norm.cdf(a, loc=theta, scale=lambd[-1])
    pivot_fn = lambda lambd, z: lambd[0] + lambd[1] * z

    probs = get_gaussian_probs(partitions, lambd_0)
    print("probs", probs.sum())
    derivative_1 = likelihood_priorpredprob_grad(alpha, probs, expert_probs)
    vmap_stochastic_derivative = jax.vmap(stochastic_derivative, in_axes=(None, 0))
    derivative_2 = vmap_stochastic_derivative(lambd_0, partitions)
    print("likelihood derivative", derivative_1)
    print("stochastic derivative", derivative_2)
    print("total stochastic derivative", jnp.dot(derivative_2.T, derivative_1))
