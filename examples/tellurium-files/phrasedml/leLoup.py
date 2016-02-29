from __future__ import print_function
import tellurium as te

phrasedmlStr = '''
  model1 = model "BIOMD0000000021.xml"
  model2 = model model1 with V_mT = 0.28, V_dT = 4.8
  simulation1 = simulate uniform(0, 380, 1000)
  task1 = run simulation1 on model1
  task2 = run simulation1 on model2
  plot task1.time vs task1.Mt, task2.Mt
  plot task1.Cn vs task1.Mt, task2.Cn vs task2.Mt
'''

exp = te.experiment(antimonyStr, phrasedmlStr)
exp.execute()
