#!/usr/bin/env python3
"""
FantasyBrain V1.0 - Validacao de Recomendacoes

Compara previsoes com resultados reais para medir performance do sistema.

Uso:
    python validar.py                # Valida todas pendentes
    python validar.py --rodada 3     # Valida rodada especifica
    python validar.py --report       # Relatorio completo
    python validar.py --all          # Revalida todas (inclusive ja validadas)
    python validar.py --detalhe 3    # Detalhe jogador a jogador da rodada
"""

import argparse
import sys
from database import (
    get_connection,
    obter_recomendacoes_pendentes,
    validar_recomendacao,
    POSICOES
)


def validar_todas_pendentes():
    """Valida todas as recomendacoes que ainda nao tem pontuacao real"""
    print("=" * 70)
    print("FANTASYBRAIN V1.0 - VALIDACAO DE RECOMENDACOES")
    print("=" * 70)

    pendentes = obter_recomendacoes_pendentes()

    if not pendentes:
        print("\nNenhuma recomendacao pendente de validacao.")
        print("Dica: gere uma recomendacao com 'python3 ia_service.py 4-3-3 100'")
        return

    print(f"\n{len(pendentes)} recomendacao(oes) pendente(s)")
    print("-" * 70)

    validadas = 0
    erros = 0

    for rec in pendentes:
        rodada = rec['rodada']
        formacao = rec['formacao']
        metodo = rec['metodo']
        pont_prev = rec['pontuacao_prevista']

        print(f"\nValidando R{rodada} ({formacao}, {metodo})...")
        print(f"  Previsto: {pont_prev:.1f} pts")

        resultado = validar_recomendacao(rec['id'])

        if resultado and resultado.get('sem_dados'):
            print(f"  [?] Sem dados reais ainda (rodada nao encerrada)")
            erros += 1
        elif resultado and resultado['pontuacao_real'] is not None:
            pont_real = resultado['pontuacao_real']
            delta = pont_real - pont_prev
            acerto_pct = (pont_real / pont_prev * 100) if pont_prev > 0 else 0

            if delta >= 0:
                ind = "[+]" if delta >= 10 else "[=]"
            else:
                ind = "[!]" if delta <= -20 else "[-]"

            print(f"  {ind} Real: {pont_real:.1f} pts | Delta: {delta:+.1f} | Acerto: {acerto_pct:.0f}%")
            validadas += 1
        else:
            print(f"  [?] Erro ao validar")
            erros += 1

    print("\n" + "=" * 70)
    print(f"Validadas: {validadas} | Sem dados: {erros}")
    print("=" * 70)


def validar_por_rodada(rodada):
    """Valida recomendacoes de uma rodada especifica"""
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT id, formacao, orcamento, metodo, pontuacao_prevista, pontuacao_real
        FROM recomendacoes_salvas
        WHERE rodada = ?
        ORDER BY criado_em DESC
    """, (rodada,))

    recs = cursor.fetchall()
    conn.close()

    if not recs:
        print(f"\nNenhuma recomendacao encontrada para rodada {rodada}")
        print("Dica: gere uma com 'python3 ia_service.py 4-3-3 100'")
        return

    print(f"\nValidando rodada {rodada}")
    print("-" * 70)

    for row in recs:
        rec_id, form, orc, metodo, prev, real = row[0], row[1], row[2], row[3], row[4], row[5]
        if real is None:
            resultado = validar_recomendacao(rec_id)
            if resultado:
                real = resultado['pontuacao_real']
                delta = real - prev
                print(f"  {form} ({metodo}): {prev:.1f} -> {real:.1f} pts (delta {delta:+.1f})")
            else:
                print(f"  {form} ({metodo}): sem dados reais")
        else:
            delta = real - prev
            print(f"  {form} ({metodo}): ja validada - {real:.1f} pts (delta {delta:+.1f})")


def mostrar_detalhe_rodada(rodada):
    """Mostra detalhe jogador a jogador de uma rodada"""
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT r.id, r.formacao, r.metodo, r.pontuacao_prevista, r.pontuacao_real,
               r.custo_total, r.orcamento
        FROM recomendacoes_salvas r
        WHERE r.rodada = ?
        ORDER BY r.criado_em DESC
        LIMIT 1
    """, (rodada,))

    rec = cursor.fetchone()
    if not rec:
        print(f"\nNenhuma recomendacao para rodada {rodada}")
        conn.close()
        return

    rec_id, formacao, metodo, pont_prev, pont_real, custo, orcamento = (
        rec[0], rec[1], rec[2], rec[3], rec[4], rec[5], rec[6]
    )

    # Validar se ainda nao foi
    if pont_real is None:
        resultado = validar_recomendacao(rec_id)
        if resultado:
            pont_real = resultado['pontuacao_real']
            # Re-read after validation
            cursor.execute("SELECT pontuacao_real FROM recomendacoes_salvas WHERE id = ?", (rec_id,))
            pont_real = cursor.fetchone()[0]

    print("=" * 80)
    print(f"DETALHE RODADA {rodada} | {formacao} | {metodo}")
    if pont_real is not None:
        delta = pont_real - pont_prev
        acerto = (pont_real / pont_prev * 100) if pont_prev > 0 else 0
        print(f"Previsto: {pont_prev:.1f} | Real: {pont_real:.1f} | Delta: {delta:+.1f} | Acerto: {acerto:.0f}%")
    else:
        print(f"Previsto: {pont_prev:.1f} | Real: aguardando dados")
    print(f"Custo: C$ {custo:.1f} / {orcamento:.1f}")
    print("=" * 80)

    # Buscar jogadores
    cursor.execute("""
        SELECT rj.jogador_id, j.apelido, rj.posicao_id, j.clube,
               rj.preco, rj.media_base, rj.media_ajustada, rj.multiplicador,
               rj.pontuacao_real, rj.is_capitao, rj.contextos, rj.mando
        FROM recomendacao_jogadores rj
        LEFT JOIN jogadores j ON rj.jogador_id = j.jogador_id
        WHERE rj.recomendacao_id = ?
        ORDER BY rj.posicao_id, rj.media_ajustada DESC
    """, (rec_id,))

    jogadores = cursor.fetchall()
    conn.close()

    pos_map = {1: 'GOL', 2: 'LAT', 3: 'ZAG', 4: 'MEI', 5: 'ATA', 6: 'TEC'}

    print(f"\n{'POS':<4} {'JOGADOR':<20} {'CLUBE':<5} {'PRECO':<7} "
          f"{'PREV':<6} {'REAL':<6} {'DELTA':<7} {'MULT':<6} {'CAP':<4}")
    print("-" * 80)

    for row in jogadores:
        jid, nome, pos_id, clube = row[0], row[1] or '?', row[2], row[3] or '?'
        preco, m_base, m_aj, mult = row[4], row[5], row[6], row[7]
        pont_r, is_cap, ctx, mando = row[8], row[9], row[10], row[11]

        pos_str = pos_map.get(pos_id, '?')
        cap_str = "[C]" if is_cap else ""
        prev_str = f"{m_aj:.1f}"

        if pont_r is not None:
            delta = pont_r - m_aj
            real_str = f"{pont_r:.1f}"
            delta_str = f"{delta:+.1f}"

            # Indicador visual
            if delta >= 3:
                ind = "+"
            elif delta <= -3:
                ind = "!"
            else:
                ind = "~"
        else:
            real_str = "---"
            delta_str = "---"
            ind = "?"

        print(f"{pos_str:<4} {nome:<20} {clube:<5} C${preco:<5.1f} "
              f"{prev_str:<6} {real_str:<6} {delta_str:<7} x{mult:<4.2f} {cap_str:<4} {ind}")

    # Se capitao, mostrar contribuicao dobrada
    capitao = [r for r in jogadores if r[9] == 1]
    if capitao and capitao[0][8] is not None:
        cap = capitao[0]
        print(f"\nCapitao {cap[1]}: {cap[8]:.1f} pts x2 = {cap[8]*2:.1f} pts de contribuicao")


def gerar_relatorio_completo():
    """Gera relatorio detalhado de todas as recomendacoes validadas"""
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT
            r.rodada, r.formacao, r.metodo,
            r.pontuacao_prevista, r.pontuacao_real,
            r.custo_total, r.orcamento, r.capitao_id,
            (SELECT j.apelido FROM jogadores j WHERE j.jogador_id = r.capitao_id) as capitao_nome,
            (SELECT rj.pontuacao_real FROM recomendacao_jogadores rj
             WHERE rj.recomendacao_id = r.id AND rj.is_capitao = 1) as capitao_pont
        FROM recomendacoes_salvas r
        WHERE r.pontuacao_real IS NOT NULL
        ORDER BY r.rodada ASC
    """)

    recs = cursor.fetchall()
    conn.close()

    if not recs:
        print("\nNenhuma recomendacao validada encontrada.")
        print("Fluxo: 1) gere recomendacao  2) sync pos-rodada  3) python3 validar.py")
        return

    print("=" * 90)
    print("RELATORIO DE PERFORMANCE - RECOMENDACOES VALIDADAS")
    print("=" * 90)

    print(f"\n{'ROD':<5} {'FORM':<6} {'METODO':<16} {'PREV':>8} {'REAL':>8} "
          f"{'DELTA':>8} {'ACERTO':>8}  {'CAPITAO':<20}")
    print("-" * 90)

    total_prev = 0
    total_real = 0
    count = 0

    for row in recs:
        rodada, form, metodo = row[0], row[1], row[2]
        prev, real = row[3], row[4]
        custo, orc = row[5], row[6]
        cap_nome, cap_pont = row[8], row[9]

        delta = real - prev
        acerto = (real / prev * 100) if prev > 0 else 0

        if delta >= 0:
            ind = "[+]" if delta >= 10 else "[=]"
        else:
            ind = "[!]" if delta <= -20 else "[-]"

        cap_str = f"{cap_nome or '?'} ({cap_pont:.1f})" if cap_pont is not None else (cap_nome or '?')

        print(f"R{rodada:<4} {form:<6} {metodo:<16} {prev:>8.1f} {real:>8.1f} "
              f"{delta:>+8.1f} {acerto:>7.0f}%  {ind} {cap_str}")

        total_prev += prev
        total_real += real
        count += 1

    print("-" * 90)
    total_delta = total_real - total_prev
    total_acerto = (total_real / total_prev * 100) if total_prev > 0 else 0

    print(f"\nACUMULADO ({count} rodada{'s' if count > 1 else ''}):")
    print(f"  Previsto: {total_prev:.1f} pts")
    print(f"  Real:     {total_real:.1f} pts")
    print(f"  Delta:    {total_delta:+.1f} pts")
    print(f"  Acerto:   {total_acerto:.0f}%")

    if count > 1:
        media_prev = total_prev / count
        media_real = total_real / count
        print(f"\n  Media por rodada: prev {media_prev:.1f} | real {media_real:.1f}")

    print("=" * 90)


def validar_todas_forcado():
    """Revalida TODAS as recomendacoes (incluindo ja validadas)"""
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("SELECT id, rodada FROM recomendacoes_salvas ORDER BY rodada")
    recs = cursor.fetchall()
    conn.close()

    if not recs:
        print("\nNenhuma recomendacao encontrada.")
        return

    print(f"\nRevalidando {len(recs)} recomendacao(oes)...")

    for rec_id, rodada in recs:
        resultado = validar_recomendacao(rec_id)
        if resultado:
            print(f"  R{rodada}: {resultado['pontuacao_real']:.1f} pts")
        else:
            print(f"  R{rodada}: erro")

    print(f"\n{len(recs)} recomendacao(oes) revalidada(s)")


def main():
    parser = argparse.ArgumentParser(
        description="FantasyBrain V1.0 - Validacao de Recomendacoes",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Exemplos:
  python validar.py                # Valida pendentes
  python validar.py --rodada 3     # Valida rodada 3
  python validar.py --detalhe 3    # Detalhe jogador a jogador R3
  python validar.py --report       # Relatorio completo
  python validar.py --all          # Revalida todas
        """
    )

    parser.add_argument("--rodada", "-r", type=int, help="Validar rodada especifica")
    parser.add_argument("--detalhe", "-d", type=int, help="Detalhe jogador a jogador de uma rodada")
    parser.add_argument("--all", action="store_true", help="Revalidar todas")
    parser.add_argument("--report", action="store_true", help="Relatorio completo")

    args = parser.parse_args()

    if args.report:
        gerar_relatorio_completo()
    elif args.all:
        validar_todas_forcado()
        print()
        gerar_relatorio_completo()
    elif args.detalhe:
        mostrar_detalhe_rodada(args.detalhe)
    elif args.rodada:
        validar_por_rodada(args.rodada)
    else:
        validar_todas_pendentes()


if __name__ == "__main__":
    main()
