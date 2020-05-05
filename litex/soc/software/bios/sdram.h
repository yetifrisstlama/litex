#ifndef __SDRAM_H
#define __SDRAM_H

#include <generated/csr.h>

void sdrsw(void);
void sdrhw(void);
void sdrrow(unsigned int row);
void sdrrdbuf(int dq);
void sdrrd(unsigned int addr, int dq);
void sdrrderr(int count);
void sdrwr(unsigned int addr);

void sdrwlon(void);
void sdrwloff(void);
int write_level(void);

int sdrlevel(void);

int memtest_silent(void);
int memtest(void);
int sdrinit(void);

#if defined(DDRPHY_CMD_DELAY) || defined(USDDRPHY_DEBUG)
void ddrphy_cdly(unsigned int delay);
#endif

#ifdef USDDRPHY_DEBUG
void sdrcal(void);
void sdrmrwr(char reg, int value);
void sdrmpr(void);
void sdr_cdly_scan(int enabled);
#endif

#endif /* __SDRAM_H */
