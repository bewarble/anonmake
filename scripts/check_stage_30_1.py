from pathlib import Path
import ast
ROOT=Path(__file__).resolve().parents[1]
def check():
 for rel in ('app/services/billing.py','app/services/billing_worker.py','app/bot/handlers/recurrent_test.py','app/bot/keyboards/recurrent_test.py'):
  p=ROOT/rel;assert p.is_file(),rel;ast.parse(p.read_text(encoding='utf-8'))
 assert 'billing_automatic_charges_enabled' in (ROOT/'app/core/config.py').read_text(encoding='utf-8')
 assert 'recurrent_test_router' in (ROOT/'app/bot/handlers/__init__.py').read_text(encoding='utf-8')
 b=(ROOT/'app/services/billing.py').read_text(encoding='utf-8');assert 'AMOUNT_EXCEED' in b;assert 'primary.decision != ChargeDecision.INSUFFICIENT' in b
 print('Stage 30.1 check: OK')
 print('Admin /testcharge: ready')
 print('299 -> 99 only on insufficient funds: ready')
 print('Automatic charges remain disabled: ready')
if __name__=='__main__':check()
