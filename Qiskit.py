



import pandas as pd
import yfinance as yf
import numpy as np
import os
import matplotlib.pyplot as plt
import neal
from qiskit import QuantumCircuit
from qiskit_aer import Aer
from scipy.optimize import minimize


global K
K = 2
global seed
seed = 123



tickers_path = 'prices.csv'

if os.path.exists(tickers_path):
    ticker_data = pd.read_csv(tickers_path)
else:
    tickers = ['GOOG', 'XOM', 'AAPL', 'AMZN', 'GLD', 'DUK', 'SO', 'AEP']
    date_range = ['2017-01-01', '2017-03-01']

    ticker_data = yf.download(
        tickers,
        start=date_range[0],
        end=date_range[1],
        group_by="ticker",
        auto_adjust=True
    )
    ticker_data = ticker_data.stack(level=0).rename_axis(['Date', 'Ticker']).reset_index()

    ticker_data.to_csv(tickers_path, index=False)
    
#computing daily log returns 

#moving data so we have index and ticker columns with adjusted prices cause PCA needs a matrix
price_df = ticker_data.pivot(index="Date", columns="Ticker", values="Close")
log_returns = np.log(price_df / price_df.shift(1)).dropna()  

#compute daily returns
data = log_returns
data.head()
    


def solve_covariance_matrix(data):
    """Calculate covariance matrix for given sample data"""
    X = data.values.T    #   8 tickers x 38 days
    J = X @ X.T          #   X transpose * X
    return J


def l1_objective(b, J):
    """
    Compute the L1 PCA objective function.
    """
    b = b.reshape(-1,1)     #   convert b to column vector
    temp = J @ b               
    B = b.T @ temp          #   matrix multiplication
    
    return -float(B[0,0])   #   scalar value
    


def solve_l1_classical_component(J, data):
    """
    Solve for a single L1 PCA component using simulated annealing.
    """
    
    from scipy.optimize import dual_annealing
    N = J.shape[0]
    bounds = [(-1,1)]*N     #   b has same width as J
    
    anneal_result = dual_annealing(lambda x: l1_objective(np.sign(x), J), bounds=bounds, seed=seed)

    B = np.sign(anneal_result.x)
    B = np.where(B == 0, 1, B)
    B = B.reshape(-1,1)
            
    prin_component = (J @ B) / np.linalg.norm(J @ B)    #   normalize
    
    temp = J @ B
    component_influence = temp @ temp.T
    
    J_final = J - component_influence     #   remove component influence
    
    return B, J_final


#########   >QISKIT SECTION<     ####################################################

def annealing_qiskit(data, gamma_list, beta_list, J, N, return_best=False):
    """
    runs the skeleton of the qiskit pca annealing
    """
    
    num_layers = 3
    qc = QuantumCircuit(N)
    
    #   HADAMARD GATE
    for i in range(N):
        qc.h(i)     
        
    qc.barrier()
    #-------------------#
    
    #   Apply main gate layers
    for i in range(num_layers):
        gamma = gamma_list[i]
        beta = beta_list[i]
        apply_cost_mixer_layers(N, J, qc, gamma, beta)
    
    #   Measure qubits to convert to classical bits
    qc.measure_all()
    
    
    """print(qc.draw())""" # <---- check what this does :D
    
    
    #   run circuit
    backend = Aer.get_backend('qasm_simulator')
    run = backend.run(qc, shots=1000)
    counts = run.result().get_counts()
    total_shots = sum(counts.values())
    expected = 0
    
    best_objective = -np.inf
    best_bitstring = None
    
    #   calculate E(X) and track best solution
    for bitstring, count in counts.items():
        b = np.array([1 if bit == '0' else -1 for bit in bitstring[::-1]])
        energy = b.T @ J @ b
        expected += energy * (count / total_shots)
        
        if energy > best_objective:
            best_objective = energy
            best_bitstring = bitstring
    
    if return_best:
        return expected, best_bitstring, best_objective
    return expected


def apply_cost_mixer_layers(N, J, qc, gamma, beta):
    """
    applies main layers of circuit (which are iterated through)
    """
    
    #   CNOT & RZ GATE
    for i in range(N):
        for j in range(i+1, N):
            if J[i,j] != 0:
                qc.cx(i,j)
                qc.rz(2*gamma*(J[i,j]),j)
                qc.cx(i,j)
                
    #   RZ(diagonal) GATE
    for i in range(N):
        if J[i,i] != 0:
            qc.rz(2*gamma*(J[i,i]),i)
    qc.barrier()
    #-------------------#
    
    #   RX GATE
    for i in range(N):
        qc.rx(2*beta,i)    
    qc.barrier()
    #-------------------#
    

def obj_func(params, J, N):
    """function for optimizer"""
    gamma_list = params[:3]     #   split parameters
    beta_list = params[3:]
    
    expected = annealing_qiskit(data, gamma_list, beta_list, J, N)
    return -expected    #   negative because we're maximizing
    

def run_annealing_qiskit(data):
    """
    main function to run QAOA optimization 
    """
    gamma_list = [0.5, 0.5, 0.5]    #   initial parameter values
    beta_list = [0.3, 0.3, 0.3]
    N = 8      #   num of qubits, 1 for each ticker
    J = solve_covariance_matrix(data)
    J = (J + J.T) / 2   #   make it symmetric - idk if necessary
    
    scale_factor = 1000
    J_scaled = J * scale_factor
    
    params = np.concatenate([gamma_list, beta_list])
    
    optimization = minimize(
        obj_func,
        params,
        args=(J_scaled, N),
        method='COBYLA',
        options={'maxiter': 50}
    )
    
    best_gamma = optimization.x[:3]
    best_beta = optimization.x[3:]
    
    # final run  to get complete results
    expectation, best_bitstring, best_objective = annealing_qiskit(
        data, best_gamma, best_beta, J_scaled, N, return_best=True
    )
    
    #   unscale back
    expectation_unscaled = expectation / scale_factor
    best_objective_unscaled = best_objective / scale_factor
    
    #   get best b from bitstring
    best_b = np.array([1 if bit == '0' else -1 for bit in best_bitstring[::-1]])
    
    print("\n=== QAOA RESULTS ===")
    print(f"Optimal gamma: {best_gamma}")
    print(f"Optimal beta: {best_beta}")
    print(f"Expectation value: {expectation_unscaled:.6f}")
    print(f"Best solution objective: {best_objective_unscaled:.6f}")
    print(f"Best bitstring: {best_bitstring}")
    print(f"Best portfolio vector b: {best_b}")
    
    return best_gamma, best_beta, expectation_unscaled, best_bitstring, best_b


#########   >QISKIT SECTION END<     ####################################################

    

def do_l1_pca(sample_data):
    """gets K principal components"""
    
    data = sample_data
    plot_array = [[],[]]
    
    J = solve_covariance_matrix(data)
    
    components = []
    
    for k in range(K):
        B, J = solve_l1_classical_component(J,data)
        components.append(B)
        
        temp = data @ B
        print('temp', temp)
        plot_array[k]=temp
        
    """
    print('plot array', plot_array)
    xaxis = plot_array[0]
    yaxis = plot_array[1]
    plt.scatter(xaxis,yaxis)  #comp 1 vs 2
    plt.ylabel('component 2')
    plt.xlabel('component 1')
    """
    return components
    
        
#do_l1_pca(data)




def convert_J_to_ising_model(J):
    """
    Converts covariance matrix J into dict of Ising Model couplings.
    """
    N = J.shape[0]
    coupl_dict = {}
    
    for x in range(N):
        for y in range(x+1, N):
            coupl_dict[(x,y)] = -J[x,y]
    
    print('dict', coupl_dict)
    return coupl_dict



def solve_l1_qapca_r_component(J):
    """quantum annealing"""
    
    coup = convert_J_to_ising_model(J)  #   ising model
    h = {}
    sampler = neal.SimulatedAnnealingSampler()
    response = sampler.sample_ising(h, coup, num_reads=100)
    
    opt = response.first.sample
    b = np.array([opt[i] for i in range (len(opt))])
    b = b.reshape(-1,1)
    
    princ_comp = (J @ b) / (np.linalg.norm(J @ b))
    b = b.reshape(-1,1)
    
    temp = J @ b
    influence = temp @ temp.T
    J_final = J - influence     #   covariance matrix
    
    print('b QUANTUM', b)
    return princ_comp, J_final
    



def solve_multi_component_qapca(J, K, epsilon, num_reads=100):
    
    """ 
    solves for K components simultaneously, 
    implements overall ising equation:
    J_ising = b^T[ I_K ⊗ KJ + (1_K - I_K)]⊗ (-εJ)b
    
    """
    
    N = J.shape[0]
    I_K = np.eye(K)             #   identity matrix dimension K
    ones_arr = np.ones((K,K))   #   matrix of 0s
    
    temp1 = np.kron(I_K, K * J) # kroneker product
    temp2 = np.kron(ones_arr - I_K, -epsilon * J)
    J_ising = temp1 + temp2
    
    coup_dict = {}              #   couplings dictionary
    h = {}                      #   bias terms
    KN = K*N 
    for x in range(KN):         #   fill ising couplings dictionary 
        for y in range(x+1, KN):
            if J_ising[x,y] != 0:
                coup_dict[(x, y)] = J_ising[x,y]
                
    #   run annealer
    sampler = neal.SimulatedAnnealingSampler()
    response = sampler.sample_ising(h, coup_dict, num_reads = num_reads, seed=seed)
    
    #   extract solution
    opt = response.first.sample
    b = np.array([opt[i] for i in range(KN)])
    
    temp = b.reshape(K,N)       #   get b as NxK matrix
    B = temp.T                  #   b as KxN matrix

    return B


def multi_component_qapca(data, K=3, epsilon=10000, num=100):
    
    """ master function for MCQAPCA """
    
    J = solve_covariance_matrix(data)
    #   call MCQAPCA function
    B = solve_multi_component_qapca(J, K, epsilon)
    
    
    X = data.values.T 
    XB = X.T @ B    #   applying b to data values
    
    # applying phi function
    U, S, Vt = np.linalg.svd(XB, full_matrices=False)
    R = U @ Vt
    
    components = [(X @ R[:, k].reshape(-1, 1)) / np.linalg.norm(X @ R[:, k]) 
                  for k in range(K)]
    
    
    print('MCQAPCA comps', components)
    
    return components




# Run QAOA and compare with classical

best_gamma, best_beta, expectation, best_bitstring, best_b = run_annealing_qiskit(data)


J = solve_covariance_matrix(data)
J = (J + J.T) / 2
B_classical, _ = solve_l1_classical_component(J, data)
classical_obj = float(B_classical.T @ J @ B_classical)
qaoa_obj = best_b.T @ J @ best_b

print(f"\nClassical solution: {B_classical.flatten()}")
print(f"Classical objective: {classical_obj:.6f}")

