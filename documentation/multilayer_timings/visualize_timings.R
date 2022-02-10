library(tidyverse)
library(ggthemes)

#setwd('~/Documents/GitHub/gcdl/documentation/multilayer_timings/')

datasets <- c("PRISM",
              "Daymet V4", 
              "CRU (multiple .nc)", 
              "CRU (single .nc)")
approaches <- c("Per month and variable",
                "Per month and variable (point to file once)",
                "Per variable",
                "Per dataset")

tfiles <- list.files(".",
                     "timing_",
                     full.names = TRUE)
all_timings <- tibble()
for(file in tfiles){
  timings <- read_csv(file) %>%
    separate(test_id, c("approach","dataset","version"), fill='right') %>%
    mutate(remote = dataset == 5,
           dataset = ifelse(dataset == 5, 2, dataset),
           dataset = factor(dataset, levels=1:4,
                            labels = datasets),
           version = ifelse(is.na(version),1,version)) %>%
    rowwise() %>%
    mutate(approach = paste(approach,version,sep="."),
           approach = factor(approach,
                             levels = c("1.1","1.2","2.1","3.1"),
                             labels = approaches)) %>%
    group_by(approach,dataset,num_years,remote) %>%
    summarise(time_sec_mean = mean(time_sec),
              time_sec_sd = sd(time_sec),
              N = n())
  
  all_timings <- all_timings %>%
    bind_rows(timings)
}


all_timings %>%
  ggplot(aes(num_years,time_sec_mean/60,color=approach)) +
  geom_line(aes(linetype=approach,group=paste(approach,remote))) +
  geom_point(aes(shape=remote)) +
  geom_errorbar(aes(ymin = (time_sec_mean-time_sec_sd)/60,
                    ymax = (time_sec_mean+time_sec_sd)/60),
                width = 0.25) +
  ylab("Processing time (minutes)") +
  xlab("No. data years processed") +
  theme_few(base_size = 8) +
  theme(legend.position = c(0.25,0.92),
        legend.background = element_blank(),
        legend.key.height = unit(0.1,'cm')) +
  facet_wrap(~dataset) +
  scale_color_colorblind(name="Approach") +
  scale_linetype_discrete(name="Approach") +
  scale_y_log10()
ggsave("xarray_timings.jpg",
       dpi = 300,
       units = 'in',
       height = 4,
       width = 6)


all_timings %>%
  mutate(time_sec = time_sec_mean/num_years) %>%
  ggplot(aes(num_years,time_sec,color=approach)) +
  geom_line(aes(linetype=approach,group=paste(approach,remote))) +
  geom_point(aes(shape=remote)) +
  geom_errorbar(aes(ymin = (time_sec_mean-time_sec_sd)/num_years,
                    ymax = (time_sec_mean+time_sec_sd)/num_years),
                width = 0.25) +
  ylab("Processing time (seconds/data year)") +
  xlab("No. data years processed") +
  theme_few(base_size = 8) +
  theme(legend.position = c(0.25,0.92),
        legend.background = element_blank(),
        legend.key.height = unit(0.1,'cm')) +
  facet_wrap(~dataset) +
  scale_color_colorblind(name="Approach") +
  scale_linetype_discrete(name="Approach") +
  scale_y_log10()
ggsave("xarray_timings_peryear.jpg",
       dpi = 300,
       units = 'in',
       height = 4,
       width = 6)
