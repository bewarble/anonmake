from __future__ import annotations
import argparse, subprocess, sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
STATIC_CHECKS=("scripts.check_final_qa","scripts.check_stage_38_1","scripts.check_stage_38_2","scripts.check_stage_38_3","scripts.check_stage_38_4","scripts.check_stage_39","scripts.check_stage_40","scripts.check_stage_41","scripts.check_stage_42","scripts.check_stage_43","scripts.check_stage_44","scripts.check_stage_45","scripts.check_stage_46","scripts.check_stage_47","scripts.check_stage_48","scripts.check_stage_49","scripts.check_stage_50","scripts.check_stage_51","scripts.check_stage_52","scripts.check_stage_53","scripts.check_stage_54","scripts.check_stage_55","scripts.check_stage_56","scripts.check_stage_57","scripts.check_stage_58","scripts.check_stage_59","scripts.check_stage_60","scripts.check_stage_61","scripts.check_stage_62","scripts.check_stage_63","scripts.check_stage_64","scripts.check_runtime_maintenance","scripts.check_multibot_isolation","scripts.check_admin_project_isolation","scripts.check_project_details_isolation","scripts.check_admin_auth_security","scripts.check_admin_csrf","scripts.check_secret_redaction","scripts.check_payment_webhook_isolation","scripts.check_payment_gateway_disable","scripts.check_admin_audit_isolation","scripts.check_deploy_safety","scripts.check_metrics_security","scripts.check_reveal_notification_race","scripts.check_public_code_aliases","scripts.check_billing_cancellation_race","scripts.check_billing_fallback_contract","scripts.check_billing_fallback_behavior","scripts.check_full_audit","scripts.check_stage_36","scripts.check_project","scripts.check_stage_34","scripts.check_stage_35","scripts.audit_active_web_assets","scripts.audit_codebase","scripts.check_product_language","scripts.audit_telegram_copy","scripts.check_bot_admin_buttons","scripts.audit_web_admin_ui","scripts.audit_route_registry","scripts.check_stage_33")
RUNTIME_CHECKS=("scripts.check_dependencies","scripts.check_migration_head","scripts.check_multibot_isolation_runtime","scripts.check_public_code_aliases_runtime","scripts.check_web_admin_runtime","scripts.check_stage_49_runtime","scripts.check_stage_60_runtime","scripts.check_stage_61_runtime","scripts.check_stage_62_runtime")
def run_module(module):
 print('\n'+'='*72+'\nRunning: '+module+'\n'+'='*72); subprocess.run([sys.executable,'-m',module],cwd=ROOT,check=True)
def main():
 p=argparse.ArgumentParser(description='AnonMake release readiness checks'); p.add_argument('--runtime',action='store_true'); p.add_argument('--runtime-only',action='store_true'); a=p.parse_args()
 if not a.runtime_only:
  for m in STATIC_CHECKS: run_module(m)
 if a.runtime or a.runtime_only:
  for m in RUNTIME_CHECKS: run_module(m)
 mode='runtime only' if a.runtime_only else ('static + runtime' if a.runtime else 'static')
 print('\nRelease check: OK\nMode:',mode)
if __name__=='__main__': main()
